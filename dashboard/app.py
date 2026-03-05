from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import get_settings
from utils.database import Database


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = settings.flask_secret_key
    db = Database(settings.database_url)

    @app.route("/")
    def index():
        summary = db.get_summary(days=30)
        recent = db.list_recent_results(limit=10)
        return render_template("index.html", summary=summary, recent=recent)

    @app.route("/emails")
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
    def stats():
        summary = db.get_summary(days=30)
        daily = db.get_daily_stats(days=30)
        return render_template("stats.html", summary=summary, daily=daily)

    @app.route("/api/stats")
    def stats_api():
        summary = db.get_summary(days=30)
        daily = db.get_daily_stats(days=30)
        return jsonify({"summary": summary, "daily": daily})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
