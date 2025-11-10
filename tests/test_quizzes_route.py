# tests/test_quizzes_route.py

import os
import sys
from pathlib import Path

# --- Rendre le package "app" importable ---
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import json
import uuid
import pytest
from app.models import Document, Question

# --- Mock Gemini : remplace la vraie génération IA ---
@pytest.fixture
def mock_generate_quiz(monkeypatch):
    def fake_generate_quiz_from_text(text, total_questions=5):
        return [
            {
                "type": "qcm",
                "question": f"Question {i+1} ?",
                "choices": ["A", "B", "C", "D"],
                "answer": "A",
                "explanation": f"Explication {i+1}"
            }
            for i in range(total_questions)
        ]
    monkeypatch.setattr("app.routes.quizzes.generate_quiz_from_text", fake_generate_quiz_from_text)

# --- TEST PRINCIPAL ---
def test_generate_quiz_route(client, db_session, mock_generate_quiz):
    """
    Vérifie que /quizzes/generate crée bien des questions pour un document.
    """
    # Créer un document en base
    doc_id = str(uuid.uuid4())
    document = Document(id=doc_id, title="Test.docx", content="Texte de test.")
    db_session.add(document)
    db_session.commit()

    # Appeler la route
    response = client.post(f"/quizzes/generate?document_id={doc_id}")
    assert response.status_code == 201

    data = response.get_json()
    assert "questions générées" in data["message"]

    # Vérifier les insertions en base
    inserted = db_session.query(Question).filter_by(document_id=doc_id).all()
    assert len(inserted) == 15  # valeur par défaut utilisée dans la route

    # Vérifier les champs d'une question
    q = inserted[0]
    assert q.type.value == "qcm"
    assert isinstance(q.choices, list)
    assert q.answer == "A"

    print(f"✅ {len(inserted)} questions insérées avec succès pour {doc_id}")
