# tests/conftest.py

import os
import sys
from pathlib import Path

# --- Rendre le package "app" importable ---
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pytest
from flask import Flask
from app.db import Base, SessionLocal, init_db
from app.routes.documents import bp as documents_bp
from app.routes.quizzes import bp as quizzes_bp


# --- Application Flask partagée pour tous les tests ---
@pytest.fixture(scope="session")
def test_app():
    """Crée une instance Flask et initialise la base SQLite en mémoire."""
    app = Flask(__name__)
    app.config["DATABASE_URL"] = "sqlite:///:memory:"
    init_db(app)

    # Enregistre les blueprints une seule fois
    app.register_blueprint(documents_bp)
    app.register_blueprint(quizzes_bp)

    yield app


# --- Client HTTP Flask ---
@pytest.fixture
def client(test_app):
    """Client Flask pour simuler les requêtes HTTP."""
    return test_app.test_client()


# --- Session SQLAlchemy ---
@pytest.fixture
def db_session():
    """Session SQLAlchemy pour les opérations directes sur la base."""
    session = SessionLocal()
    yield session
    session.close()


# --- Nettoyage automatique de la base avant chaque test ---
@pytest.fixture(autouse=True)
def clean_db():
    """Vide toutes les tables avant chaque test pour éviter les interférences."""
    session = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()