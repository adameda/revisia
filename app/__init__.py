from flask import Flask
from datetime import datetime
from flask_login import current_user
from .db import init_db
from . import models
from .routes import documents, ui, quizzes, results, auth
from .routes.auth import login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE_URL="sqlite:///data.db"
    )

    # --- Base de données ---
    init_db(app)

    # --- Authentification ---
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # --- Blueprints ---
    app.register_blueprint(auth.bp)
    app.register_blueprint(documents.bp)
    app.register_blueprint(quizzes.bp)
    app.register_blueprint(results.bp)
    app.register_blueprint(ui.bp)

    # --- Variables globales ---
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "Révis'IA",
            "app_tagline": "Tes cours transformés en quiz",
            "current_year": datetime.now().year,
            "current_user": current_user
        }

    return app