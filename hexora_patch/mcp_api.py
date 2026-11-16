"""Token-protected HEXORA API bridge for the MCP server.

Review database columns and helper signatures against the deployed HEXORA revision
before registering this blueprint.
"""
import hmac
import json
import os

from database import begin_write_transaction, get_db
from flask import Blueprint, abort, g, jsonify, request
from question_ids import format_question_number, parse_question_number
from question_repository import _question_row
from question_revisions import _insert_question_revision, _question_snapshot
from question_validation import _collect_question_data
from werkzeug.datastructures import MultiDict

mcp_api = Blueprint("mcp_api", __name__, url_prefix="/api/integrations/mcp")

@mcp_api.before_request
def authorize():
    expected = os.environ.get("HEXORA_MCP_API_TOKEN", "")
    header = request.headers.get("Authorization", "")
    supplied = header[7:] if header.startswith("Bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(401)
    author_uuid = os.environ.get("HEXORA_MCP_SERVICE_USER_UUID", "")
    if not author_uuid:
        abort(503, description="HEXORA_MCP_SERVICE_USER_UUID is not configured")
    user = get_db().execute("SELECT uuid, email, display_name, role FROM users WHERE uuid = ?",
                            (author_uuid,)).fetchone()
    if user is None: abort(503, description="Configured service author does not exist")
    g.user = user

@mcp_api.get("/health")
def health():
    return jsonify({"ok": True, "service": "HEXORA", "integration": "mcp"})

@mcp_api.get("/questions")
def search_questions():
    q = request.args.get("query", "").strip()
    filters = {k: request.args.get(k, "").strip() for k in
               ("subject", "grade", "achievement_standard", "difficulty")}
    limit = min(max(request.args.get("limit", 10, type=int), 1), 50)
    sql = """SELECT id,title,subject,grade,course,curriculum,unit,achievement_standard,
             difficulty,question_type,points,prompt,choices,answer,explanation,source,
             source_url,license FROM questions WHERE deleted_at IS NULL"""
    args = []
    for col, value in filters.items():
        if value: sql += f" AND {col} = ?"; args.append(value)
    if q:
        sql += " AND (title LIKE ? OR prompt LIKE ? OR explanation LIKE ?)"
        args.extend([f"%{q}%"] * 3)
    sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    rows = get_db().execute(sql, args).fetchall()
    items = []
    for row in rows:
        item = dict(row); item["code"] = format_question_number(item.pop("id"))
        try: item["choices"] = json.loads(item.get("choices") or "[]")
        except (ValueError, TypeError): item["choices"] = []
        items.append(item)
    return jsonify({"ok": True, "count": len(items), "questions": items})

@mcp_api.get("/questions/<code>")
def get_question(code):
    ident = parse_question_number(code)
    if ident is None: abort(404)
    row = _question_row(ident)
    if row["deleted_at"] is not None: abort(404)
    item = dict(row); item["code"] = format_question_number(item.pop("id"))
    try: item["choices"] = json.loads(item.get("choices") or "[]")
    except (ValueError, TypeError): item["choices"] = []
    return jsonify({"ok": True, "question": item})

@mcp_api.get("/standards")
def standards():
    try:
        from question_constants import CURRICULUM_STANDARDS
    except ImportError:
        return jsonify({"ok": False, "standards": [], "error": "Standards source unavailable"}), 503
    query = request.args.get("query", "").strip()
    curriculum = request.args.get("curriculum", "2022 개정 교육과정")
    subject = request.args.get("subject", "").strip()
    limit = min(max(request.args.get("limit", 30, type=int), 1), 100)
    data = CURRICULUM_STANDARDS.get(curriculum, {})
    found = []
    for subj, units in data.items():
        if subject and subject != subj: continue
        for unit, standards_list in units.items():
            for standard in standards_list:
                if query and query not in standard and query not in unit: continue
                found.append({"curriculum": curriculum, "subject": subj,
                              "unit": unit, "achievement_standard": standard})
    return jsonify({"ok": True, "count": min(len(found), limit), "standards": found[:limit]})

def collect(payload):
    form = MultiDict()
    for key, value in payload.items():
        if key == "choices" and isinstance(value, list): form.add(key, "\n".join(map(str, value)))
        elif value is not None: form.add(key, str(value))
    return _collect_question_data(form)

@mcp_api.post("/questions/validate")
def validate():
    _data, errors = collect(request.get_json(silent=True) or {})
    return jsonify({"ok": True, "valid": not errors, "errors": errors})

@mcp_api.post("/questions")
def create():
    body = request.get_json(silent=True) or {}
    data, errors = collect(body.get("question") or {})
    if errors: return jsonify({"ok": False, "created": False, "errors": errors}), 400
    db = get_db()
    try:
        begin_write_transaction(db)
        cur = db.execute("""INSERT INTO questions
        (user_uuid,folder_uuid,subject,grade,unit,passage,prompt,examples,choices,answer,
         explanation,source,year,page,difficulty,question_type,points,course,curriculum,
         achievement_standard,source_type,exam,original_question_number,source_url,license,title)
        VALUES (?,NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
        (g.user["uuid"],data["subject"],data["grade"],data["unit"],data["passage"],data["prompt"],
         data["examples"],json.dumps(data["choices"],ensure_ascii=False),data["answer"],
         data["explanation"],data["source"],data["year"],data["page"],data["difficulty"],
         data["question_type"],data["points"],data["course"],data["curriculum"],
         data["achievement_standard"],data["source_type"],data["exam"],
         data["original_question_number"],data["source_url"],data["license"],data["title"]))
        ident = cur.fetchone()["id"]
        row = db.execute("SELECT * FROM questions WHERE id = ?", (ident,)).fetchone()
        _insert_question_revision(db, ident, 1, g.user["uuid"],
                                  "ChatGPT MCP 최초 등록", _question_snapshot(row))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return jsonify({"ok": True, "created": True, "code": format_question_number(ident)}), 201
