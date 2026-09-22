"""Application factory for LANShare 50."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import AppConfig


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config.from_object(AppConfig)

    if test_config:
        app.config.update(test_config)

    from .routes.api import api_bp

    app.register_blueprint(api_bp)

    return app
