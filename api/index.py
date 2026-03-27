"""
LegalConsult AI - Vercel Serverless Entry Point (v2)
Attempts FastAPI+Mangum first, falls back to lightweight Flask if FastAPI init fails.
This resolves Internal Server Error on Vercel Python runtime.
"""
import os
import sys
import logging
import pathlib
import json
import sqlite3

logger = logging.getLogger("legalconsult.vercel")

# Ensure project root is in path
project_root = str(pathlib.Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DATABASE_PATH", "/tmp/legalconsult.db")

# ─── Attempt 1: FastAPI + Mangum (preferred) ───
try:
    from main import app
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    logger.info("LegalConsult FastAPI handler created successfully")
except Exception as fastapi_err:
    logger.warning(f"FastAPI init failed: {fastapi_err}, falling back to Flask")
    
    # ─── Attempt 2: Lightweight Flask fallback ───
    from flask import Flask, jsonify, request
    
    _app = Flask(__name__)
    DB_PATH = "/tmp/legalconsult.db"
    
    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db():
        conn = get_db()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            skill_type TEXT DEFAULT 'legal_qa',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            review_result TEXT,
            risk_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        conn.commit()
        conn.close()
    
    try:
        init_db()
    except Exception as e:
        logger.error(f"Flask fallback DB init failed: {e}")
    
    # Load knowledge base
    kb = {}
    kb_dir = pathlib.Path(project_root) / "knowledge_base"
    if kb_dir.exists():
        for f in kb_dir.glob("*.md"):
            try:
                kb[f.stem] = f.read_text(encoding="utf-8")[:2000]
            except Exception:
                pass
        for f in kb_dir.glob("*.json"):
            try:
                kb[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    
    @_app.route("/")
    def index():
        return jsonify({
            "name": "LegalConsult AI - 中国法律咨询AI",
            "version": "0.1.0",
            "mode": "flask-fallback",
            "fastapi_error": str(fastapi_err),
            "endpoints": [
                "GET /",
                "GET /api/health",
                "GET /api/knowledge",
                "POST /api/consult",
                "GET /api/consultations",
                "POST /api/review-contract",
                "GET /api/contracts",
            ]
        })
    
    @_app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "mode": "flask-fallback", "db": os.path.exists(DB_PATH), "kb_keys": list(kb.keys())})
    
    @_app.route("/api/knowledge")
    def knowledge():
        return jsonify({k: (v[:500] + "..." if isinstance(v, str) and len(v) > 500 else v) for k, v in kb.items()})
    
    @_app.route("/api/consult", methods=["POST"])
    def consult():
        data = request.get_json(force=True)
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        # Simple keyword-based legal Q&A (no LLM needed)
        answer = "感谢您的咨询。建议您提供更多具体信息，或联系专业律师获取详细法律意见。"
        keywords_map = {
            "合同": "根据《中华人民共和国合同法》，合同是平等主体的自然人、法人、其他组织之间设立、变更、终止民事权利义务关系的协议。合同的订立应当遵循自愿、公平、诚实信用原则。",
            "劳动": "根据《中华人民共和国劳动法》和《劳动合同法》，劳动者享有平等就业和选择职业的权利、取得劳动报酬的权利、休息休假的权利等。",
            "债务": "根据《民法典》，债务应当清偿。债权人有权要求债务人按照合同的约定或者依照法律的规定履行义务。",
            "离婚": "根据《民法典》婚姻家庭编，夫妻双方自愿离婚的，应当签订书面离婚协议，并亲自到婚姻登记机关申请离婚登记。",
            "知识产权": "根据《民法典》和相关知识产权法律，知识产权是权利人依法就作品、发明、商标等享有的专有权利。",
        }
        for kw, resp in keywords_map.items():
            if kw in question:
                answer = resp
                break
        conn = get_db()
        conn.execute("INSERT INTO consultations (client_name, question, answer) VALUES (?, ?, ?)",
                    (data.get("client_name", "匿名"), question, answer))
        conn.commit()
        conn.close()
        return jsonify({"question": question, "answer": answer})
    
    @_app.route("/api/consultations", methods=["GET"])
    def list_consultations():
        conn = get_db()
        items = [dict(row) for row in conn.execute("SELECT * FROM consultations ORDER BY created_at DESC LIMIT 50").fetchall()]
        conn.close()
        return jsonify(items)
    
    @_app.route("/api/review-contract", methods=["POST"])
    def review_contract():
        data = request.get_json(force=True)
        content = data.get("content", "").strip()
        if not content:
            return jsonify({"error": "content is required"}), 400
        # Simple rule-based contract review
        risks = []
        risk_score = 100
        risk_patterns = {
            "无固定期限": ("未约定合同期限，可能导致合同效力争议", 15),
            "不可抗力": ("缺少不可抗力条款，建议补充", 10),
            "仲裁": ("约定了仲裁条款，请确认仲裁机构", 5),
            "违约金": ("违约金条款需注意合理性", 5),
            "保密": ("建议增加保密条款", 8),
        }
        for pattern, (desc, penalty) in risk_patterns.items():
            if pattern in content:
                risks.append({"rule": pattern, "description": desc, "severity": "warning"})
                risk_score -= penalty
        if not risks:
            risks.append({"rule": "general", "description": "未发现明显风险，建议专业律师复核", "severity": "info"})
        risk_score = max(0, risk_score)
        conn = get_db()
        conn.execute("INSERT INTO contracts (title, content, review_result, risk_score) VALUES (?, ?, ?, ?)",
                    (data.get("title", "未命名合同"), content[:500], json.dumps(risks, ensure_ascii=False), risk_score))
        conn.commit()
        conn.close()
        return jsonify({"risk_score": risk_score, "risks": risks})
    
    @_app.route("/api/contracts", methods=["GET"])
    def list_contracts():
        conn = get_db()
        items = [dict(row) for row in conn.execute("SELECT * FROM contracts ORDER BY created_at DESC LIMIT 50").fetchall()]
        conn.close()
        return jsonify(items)
    
    handler = _app
    logger.info("LegalConsult Flask fallback handler created")
