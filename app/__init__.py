from flask import Flask, render_template
from datetime import datetime
from flask_login import current_user
import os
import logging
from dotenv import load_dotenv
from .db import init_db
from . import models
from .extensions import csrf, limiter
from .routes import documents, ui, quizzes, results, auth, subjects, groups, events
from .routes.auth import login_manager

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        DEBUG=os.getenv("DEBUG", "False").lower() == "true",
        MOCK_GEMINI=os.getenv("MOCK_GEMINI", "False").lower() == "true",
        DAILY_QUIZ_LIMIT=int(os.getenv("DAILY_QUIZ_LIMIT", "10")),
        REGISTRATION_ENABLED=os.getenv("REGISTRATION_ENABLED", "True").lower() == "true",
        QUIZ_LIMIT_ENABLED=os.getenv("QUIZ_LIMIT_ENABLED", "False").lower() == "true",
    )

    # --- Logging ---
    # Configure le format des logs envoyés dans la console (stdout).
    # Railway capture automatiquement tout ce qui sort dans stdout.
    # Format : [date heure] NIVEAU module - message
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Remplace les handlers existants (évite les doublons)
    )
    # Réduire le bruit de SQLAlchemy (trop verbeux par défaut)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # --- Base de données ---
    init_db(app)

    # --- Authentification ---
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # --- Sécurité CSRF + Rate Limiter ---
    csrf.init_app(app)
    limiter.init_app(app)

    # --- Headers de sécurité ---
    # Ajoutés automatiquement à CHAQUE réponse HTTP.
    # Ils indiquent au navigateur comment se protéger.
    @app.after_request
    def set_security_headers(response):
        # Empêche le navigateur de deviner le type de fichier (évite l'exécution de scripts déguisés)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Empêche d'afficher le site dans une iframe externe (anti-clickjacking)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # --- Pages d'erreur personnalisées ---
    # Sans ça, Flask affiche une page blanche moche sur les erreurs.
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        logging.getLogger("app").error(f"Erreur 500 : {e}")
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("errors/429.html"), 429

    # --- Blueprints ---
    app.register_blueprint(auth.bp)
    app.register_blueprint(documents.bp)
    app.register_blueprint(quizzes.bp)
    app.register_blueprint(results.bp)
    app.register_blueprint(subjects.bp)
    app.register_blueprint(groups.groups_bp)
    app.register_blueprint(events.events_bp)
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
            "debug_mode": app.config.get("DEBUG", False),
            "registration_enabled": app.config.get("REGISTRATION_ENABLED", True),
            "quiz_limit_enabled": app.config.get("QUIZ_LIMIT_ENABLED", False),
        }

    return app