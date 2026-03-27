"""
LegalConsult AI - Vercel Serverless Entry Point (v3 - Pure Flask)
Self-contained Flask app. No FastAPI imports. No heavy dependencies.
Definitive fix for Vercel Python 500 errors.
"""
import os
import sys
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "/tmp/legalconsult.db"

# ─── Database ───
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL, question TEXT NOT NULL, answer TEXT,
        skill_type TEXT DEFAULT 'legal_qa', created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Config ───
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ─── Skills ───
SKILLS = {
    "contract_review": {"name": "合同审查", "icon": "📋"},
    "legal_qa": {"name": "法律问答", "icon": "❓"},
    "compliance_check": {"name": "企业合规检查", "icon": "✅"},
    "labor_dispute": {"name": "劳动争议咨询", "icon": "👷"},
    "ip_protection": {"name": "知识产权保护", "icon": "🔒"},
    "debt_collection": {"name": "债务催收指导", "icon": "💰"},
}

# ═══ Routes ═══

@app.route("/")
def index():
    return jsonify({
        "name": "LegalConsult AI",
        "version": "1.0.0",
        "mode": "vercel-flask-v3",
        "skills": list(SKILLS.keys())
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "mode": "flask-v3", "llm": bool(DEEPSEEK_API_KEY)})

@app.route("/api/skills")
def list_skills():
    return jsonify({"skills": SKILLS, "llm_configured": bool(DEEPSEEK_API_KEY)})

@app.route("/api/consult", methods=["POST"])
def consult():
    data = request.get_json(force=True)
    skill_type = data.get("skill_type", "legal_qa")
    question = data.get("question", "").strip()
    
    if skill_type not in SKILLS:
        return jsonify({"error": f"unknown skill: {skill_type}"}), 400
    
    # Template fallback
    if "合同" in question:
        answer = "合同审查要点：1)主体资格 2)权利义务对等 3)付款条款明确 4)争议解决方式"
    elif "劳动" in question:
        answer = "劳动争议要点：未签合同→双倍工资；违法解除→2N赔偿；加班费→1.5/2/3倍"
    else:
        answer = f"您的问题：{question[:100]}... 建议：1)收集证据 2)注意3年诉讼时效 3)协商→调解→仲裁→诉讼"
    
    return jsonify({"skill_type": skill_type, "question": question, "answer": answer})

# Vercel handler
handler = app
