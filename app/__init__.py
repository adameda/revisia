from flask import Flask
from datetime import datetime
from flask_login import current_user
import os
from dotenv import load_dotenv
from .db import init_db
from . import models
from .routes import documents, ui, quizzes, results, auth, subjects
from .routes.auth import login_manager

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE_URL="sqlite:///data.db",
        DEBUG=os.getenv("DEBUG", "False").lower() == "true",
        MOCK_GEMINI=os.getenv("MOCK_GEMINI", "False").lower() == "true"
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
    app.register_blueprint(subjects.bp)
    app.register_blueprint(ui.bp)

    # --- Variables globales ---
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "Révis'IA",
            "app_tagline": "Tes cours transformés en quiz",
            "current_year": datetime.now().year,
            "current_user": current_user,
            "mock_mode": app.config.get("MOCK_GEMINI", False),
            "debug_mode": app.config.get("DEBUG", False)
        }

    return app