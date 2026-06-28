from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

try:
    from flask import Flask, jsonify, request, send_from_directory
except ModuleNotFoundError:
    hermes_python = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3"
    if hermes_python.exists() and Path(sys.executable).resolve() != hermes_python.resolve():
        os.execv(str(hermes_python), [str(hermes_python), *sys.argv])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, jsonify, request, send_from_directory

from agent_engine import AgentEngine
from brain_store import BrainStore
from gpt_client import GPTClient

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
brain = BrainStore(DATA / "company_brain.json")
engine = AgentEngine(brain, GPTClient())


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/brain")
def get_brain():
    return jsonify({"rules": brain.all_rules()})


@app.post("/api/brain/reset")
def reset_brain():
    brain.reset()
    engine.reset_runtime()
    return jsonify({"ok": True, "rules": [], "roster": []})


@app.post("/api/brain/seed")
def seed_brain():
    rules = brain.seed_samples()
    return jsonify({"ok": True, "rules": rules})


@app.post("/api/onboard")
def onboard():
    payload = request.get_json(force=True, silent=True) or {}
    trigger = (payload.get("trigger") or "").strip()
    if not trigger:
        return jsonify({"error": "Trigger is required"}), 400
    return jsonify(engine.onboard(trigger))


@app.post("/api/resolve")
def resolve():
    payload = request.get_json(force=True, silent=True) or {}
    employee_id = payload.get("employee_id")
    department = payload.get("department")
    if department not in ("Sales", "Engineering"):
        return jsonify({"error": "Resolution must be Sales or Engineering"}), 400
    try:
        rule = engine.resolve(employee_id, department)
    except KeyError:
        return jsonify({"error": "No pending ambiguity for that employee"}), 404
    return jsonify({"ok": True, "rule": rule, "brain": {"rules": brain.all_rules()}, "roster": engine.roster})


@app.post("/api/brain/query")
def query_brain():
    payload = request.get_json(force=True, silent=True) or {}
    query = (payload.get("query") or "").strip()
    if not query:
        return jsonify({"answer": "Ask a question about stored company decisions.", "sources": []})
    return jsonify(engine.query_brain(query))


@app.get("/api/roster")
def roster():
    return jsonify({"roster": engine.roster})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
