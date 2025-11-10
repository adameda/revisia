# tests/test_full_flow.py

import os
import sys
from pathlib import Path

# --- Rendre le package "app" importable ---
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import io
import json
import uuid
import pytest
from app.models import Document, Question

# --- Mock de Markitdown (extraction de texte à partir du docx) ---
@pytest.fixture
def mock_extract(monkeypatch):
    def fake_extract_text_from_docx(file_path: str) -> str:
        return "Texte extrait simulé du document .docx pour test."
    monkeypatch.setattr("app.routes.documents.extract_text_from_docx", fake_extract_text_from_docx)


# --- Mock de la génération IA Gemini ---
@pytest.fixture
def mock_generate(monkeypatch):
    def fake_generate_quiz_from_text(text, total_questions=10):
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


# --- TEST COMPLET DU FLUX UPLOAD → GENERATE ---
def test_upload_then_generate_quiz(client, db_session, mock_extract, mock_generate):
    """
    Vérifie le flux complet :
    1. Upload d'un document .docx
    2. Génération automatique du quiz
    """
    # Simuler l'upload d'un fichier DOCX factice
    data = {
        "file": (io.BytesIO(b"Fake DOCX binary content"), "cours_test.docx")
    }
    upload_response = client.post("/documents/upload", content_type="multipart/form-data", data=data)
    assert upload_response.status_code == 201

    upload_data = upload_response.get_json()
    doc_id = upload_data["document_id"]
    assert "cours_test.docx" in upload_data["title"]

    # Appeler la route de génération du quiz
    quiz_response = client.post(f"/quizzes/generate?document_id={doc_id}")
    assert quiz_response.status_code == 201

    quiz_data = quiz_response.get_json()
    assert "questions générées" in quiz_data["message"]

    # Vérifier les insertions dans la base
    inserted = db_session.query(Question).filter_by(document_id=doc_id).all()
    assert len(inserted) == 15  # nombre utilisé dans la route
    assert all(q.type.value == "qcm" for q in inserted)

    print(f"Flux complet OK — {len(inserted)} questions créées pour le document {doc_id}")
