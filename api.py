"""
api.py — JobOps Dashboard API Server
Serves job evaluation data from SQLite to the dashboard.

Usage:
    python api.py

Runs on http://localhost:5050
"""

import json
import os
import queue
import sqlite3
import time
import threading
from flask import Flask, jsonify, request, send_file, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=False)

DB_PATH = os.path.join(".users", "chase_lavalley", "jobs.db")


@app.route("/")
def dashboard():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html"))


def get_db():
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_row(row):
    """Convert a DB row to a clean dict, parsing JSON fields."""
    d = dict(row)
    for field in ["benefits", "gate_details", "null_fields", "scores", "gaps"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    d["gate_passed"] = bool(d.get("gate_passed"))
    return d


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Return all evaluated jobs, sorted by composite_score desc."""
    conn = get_db()
    if not conn:
        return jsonify({"jobs": [], "total": 0, "error": "jobs.db not found"})

    try:
        cursor = conn.execute("""
            SELECT * FROM evaluations
            ORDER BY composite_score DESC
        """)
        jobs = [parse_row(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"jobs": jobs, "total": len(jobs)})
    except sqlite3.Error as e:
        return jsonify({"jobs": [], "total": 0, "error": str(e)})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """Return a single job by job_id."""
    conn = get_db()
    if not conn:
        return jsonify({"error": "jobs.db not found"}), 404

    try:
        cursor = conn.execute(
            "SELECT * FROM evaluations WHERE job_id = ?", (job_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(parse_row(row))
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Return summary stats for the dashboard header."""
    conn = get_db()
    if not conn:
        return jsonify({"total": 0, "apply": 0, "review": 0, "skip": 0, "avg_score": 0})

    try:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN recommendation = 'APPLY'  THEN 1 ELSE 0 END) as apply,
                SUM(CASE WHEN recommendation = 'REVIEW' THEN 1 ELSE 0 END) as review,
                SUM(CASE WHEN recommendation = 'SKIP'   THEN 1 ELSE 0 END) as skip,
                ROUND(AVG(composite_score), 2) as avg_score
            FROM evaluations
        """)
        row = cursor.fetchone()
        conn.close()
        return jsonify(dict(row))
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/run", methods=["POST"])
def run_command():
    """
    Execute a Claude Code slash command in the repo directory.
    Body: { "command": "/evaluate", "url": "https://..." }
    Returns streaming text output from claude -p.
    """
    import subprocess
    import threading

    data = request.get_json()
    command = data.get("command", "").strip()
    url     = data.get("url", "").strip()

    if not command or not url:
        return jsonify({"error": "command and url are required"}), 400

    if not url.startswith("http"):
        return jsonify({"error": "invalid URL"}), 400

    allowed = ["/evaluate", "/apply", "/generate_docs"]
    if command not in allowed:
        return jsonify({"error": f"command must be one of {allowed}"}), 400

    full_prompt = f"{command} {url}"
    repo_root   = os.path.dirname(os.path.abspath(__file__))

    def generate():
        try:
            proc = subprocess.Popen(
              ["claude", "-p", full_prompt],
              cwd=repo_root,
              stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT,
              text=True,
              encoding="utf-8",
              errors="replace",
              bufsize=1
            )
            if proc.stdout:
              for line in proc.stdout:
                yield line
            proc.wait()
            yield f"\n[EXIT {proc.returncode}]\n"
        except FileNotFoundError:
            yield "[ERROR] claude CLI not found — is Claude Code installed and on PATH?\n"
        except Exception as e:
            yield f"[ERROR] {str(e)}\n"

    return app.response_class(generate(), mimetype="text/plain")


@app.route("/api/generate_docs", methods=["POST"])
def generate_docs():
    """
    Generate documents for a job by job_id.
    Body: { "job_id": "string" }
    Streams stdout from: claude --dangerously-skip-permissions -p "/generate_docs {job_id}"
    """
    import subprocess

    data = request.get_json()
    job_id = (data.get("job_id") or "").strip()

    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    conn = get_db()
    if not conn:
        return jsonify({"error": "jobs.db not found"}), 404

    try:
        cursor = conn.execute(
            "SELECT job_id FROM evaluations WHERE job_id = ?", (job_id,)
        )
        row = cursor.fetchone()
        conn.close()
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    if not row:
        return jsonify({"error": "job not found"}), 404

    repo_root = os.path.dirname(os.path.abspath(__file__))

    def generate():
        try:
            proc = subprocess.Popen(
                ["claude", "--dangerously-skip-permissions", "-p", f"/generate_docs {job_id}"],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
            line_queue = queue.Queue()

            def reader():
                try:
                    for line in proc.stdout:
                        line_queue.put(line)
                finally:
                    line_queue.put(None)

            threading.Thread(target=reader, daemon=True).start()

            while True:
                try:
                    line = line_queue.get(timeout=15)
                    if line is None:
                        break
                    yield line
                except queue.Empty:
                    yield " \n"  # keepalive heartbeat

            try:
                proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                proc.kill()
                yield "[ERROR] Process timed out after 600 seconds\n"
                return

            yield f"\n[EXIT {proc.returncode}]\n"
        except FileNotFoundError:
            yield "[ERROR] claude CLI not found — is Claude Code installed and on PATH?\n"
        except Exception as e:
            yield f"[ERROR] {str(e)}\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
        }
    )


if __name__ == "__main__":
    print("JobOps API running at http://localhost:5050")
    print(f"Database: {os.path.abspath(DB_PATH)}")
    app.run(host='0.0.0.0', port=5050, debug=True, threaded=True)