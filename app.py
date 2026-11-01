"""
BugBoard — A lightweight issue tracker built with Flask.
Developed as a cloud-native application for CSA3004 Cloud Native Orchestration.
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bugboard-secret-key-2026")

DATABASE = os.environ.get("DATABASE_PATH", "bugboard.db")


# --------------- Database helpers ---------------

def get_db():
    """Open a new database connection."""
    db_path = os.environ.get("DATABASE_PATH", DATABASE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they do not exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL DEFAULT '',
            priority    TEXT    NOT NULL DEFAULT 'Medium',
            status      TEXT    NOT NULL DEFAULT 'Open',
            created_by  TEXT    NOT NULL DEFAULT 'Anonymous',
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# --------------- Routes ---------------

@app.route("/")
def index():
    """Dashboard — list all issues with optional filters."""
    status_filter = request.args.get("status", "All")
    priority_filter = request.args.get("priority", "All")
    search_query = request.args.get("q", "").strip()

    conn = get_db()
    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if priority_filter != "All":
        query += " AND priority = ?"
        params.append(priority_filter)

    if search_query:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    query += " ORDER BY id DESC"
    issues = conn.execute(query, params).fetchall()

    # Stats for the dashboard cards
    total = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    open_count = conn.execute("SELECT COUNT(*) FROM issues WHERE status='Open'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM issues WHERE status='In Progress'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM issues WHERE status IN ('Resolved','Closed')").fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        issues=issues,
        total=total,
        open_count=open_count,
        in_progress=in_progress,
        resolved=resolved,
        status_filter=status_filter,
        priority_filter=priority_filter,
        search_query=search_query,
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    """Create a new issue."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        created_by = request.form.get("created_by", "").strip() or "Anonymous"

        if not title:
            flash("Title is required.", "error")
            return render_template("create.html")

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        conn.execute(
            "INSERT INTO issues (title, description, priority, status, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, 'Open', ?, ?, ?)",
            (title, description, priority, created_by, now, now),
        )
        conn.commit()
        conn.close()
        flash("Issue created successfully.", "success")
        return redirect(url_for("index"))

    return render_template("create.html")


@app.route("/edit/<int:issue_id>", methods=["GET", "POST"])
def edit(issue_id):
    """Edit an existing issue."""
    conn = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        status = request.form.get("status", "Open")

        if not title:
            flash("Title is required.", "error")
            issue = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
            conn.close()
            return render_template("edit.html", issue=issue)

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE issues SET title=?, description=?, priority=?, status=?, updated_at=? WHERE id=?",
            (title, description, priority, status, now, issue_id),
        )
        conn.commit()
        conn.close()
        flash("Issue updated successfully.", "success")
        return redirect(url_for("index"))

    issue = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()

    if issue is None:
        flash("Issue not found.", "error")
        return redirect(url_for("index"))

    return render_template("edit.html", issue=issue)


@app.route("/delete/<int:issue_id>", methods=["POST"])
def delete(issue_id):
    """Delete an issue."""
    conn = get_db()
    conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    flash("Issue deleted.", "success")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return jsonify({"status": "healthy", "app": "BugBoard", "version": "1.0.0"}), 200


# --------------- Startup ---------------

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
