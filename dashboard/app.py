from __future__ import annotations

import secrets
import sys
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import get_settings, update_env_values
from utils.database import Database


def _verify_password(stored_password: str, provided_password: str) -> bool:
    if not stored_password:
        return False

    # Accept either plain text password or werkzeug hash in environment.
    if stored_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        try:
            return bool(check_password_hash(stored_password, provided_password))
        except ValueError:
            return False

    return secrets.compare_digest(stored_password, provided_password)


def _safe_next_path(raw_next: str | None) -> str:
    if raw_next and raw_next.startswith("/") and not raw_next.startswith("//"):
        return raw_next
    return "/"


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = settings.flask_secret_key
    db = Database(settings.database_url)

    def is_authenticated() -> bool:
        return bool(session.get("auth_ok"))

    def login_required(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                return redirect(url_for("login", next=request.path))
            return view_func(*args, **kwargs)

        return wrapper

    @app.context_processor
    def inject_user_context():
        return {
            "is_authenticated": is_authenticated(),
            "current_user": session.get("username", ""),
        }

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if is_authenticated():
            return redirect(url_for("index"))

        error = ""
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            if (
                secrets.compare_digest(username, settings.dashboard_username)
                and _verify_password(settings.dashboard_password, password)
            ):
                session.clear()
                session["auth_ok"] = True
                session["username"] = username
                target = _safe_next_path(request.args.get("next"))
                return redirect(target)

            error = "Логин немесе құпиясөз қате."

        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        summary = db.get_summary(days=30)
        recent = db.list_recent_results(limit=10)
        return render_template("index.html", summary=summary, recent=recent)

    @app.route("/emails")
    @login_required
    def emails():
        page = max(int(request.args.get("page", 1)), 1)
        per_page = 20
        offset = (page - 1) * per_page
        items = db.list_recent_results(limit=per_page, offset=offset)
        total = db.count_results()
        total_pages = (total + per_page - 1) // per_page
        return render_template(
            "emails.html",
            items=items,
            page=page,
            total_pages=max(total_pages, 1),
        )

    @app.route("/stats")
    @login_required
    def stats():
        summary = db.get_summary(days=30)
        daily = db.get_daily_stats(days=30)
        return render_template("stats.html", summary=summary, daily=daily)

    @app.route("/api/stats")
    @login_required
    def stats_api():
        summary = db.get_summary(days=30)
        daily = db.get_daily_stats(days=30)
        return jsonify({"summary": summary, "daily": daily})

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings_page():
        if request.method == "POST":
            threshold_raw = (request.form.get("phishing_threshold") or "").strip()
            interval_raw = (request.form.get("scan_interval_minutes") or "").strip()

            try:
                threshold = float(threshold_raw)
                if not 0.0 < threshold < 1.0:
                    raise ValueError
            except ValueError:
                return (
                    render_template(
                        "settings.html",
                        settings=get_settings(),
                        saved=False,
                        error="PHISHING_THRESHOLD мәні 0 мен 1 арасында болуы керек.",
                    ),
                    400,
                )

            try:
                interval = int(interval_raw)
                if not 1 <= interval <= 1440:
                    raise ValueError
            except ValueError:
                return (
                    render_template(
                        "settings.html",
                        settings=get_settings(),
                        saved=False,
                        error="SCAN_INTERVAL_MINUTES мәні 1 мен 1440 арасында болуы керек.",
                    ),
                    400,
                )

            update_env_values(
                {
                    "PHISHING_THRESHOLD": str(threshold),
                    "SCAN_INTERVAL_MINUTES": str(interval),
                }
            )
            return redirect(url_for("settings_page", saved="1"))

        saved = request.args.get("saved") == "1"
        return render_template(
            "settings.html",
            settings=get_settings(),
            saved=saved,
            error="",
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
