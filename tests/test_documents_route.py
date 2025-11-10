# tests/test_documents_route.py

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
from app.models import Document, Question, QuestionType

# --- Mock Markitdown ---
@pytest.fixture
def mock_extract(monkeypatch):
    def fake_extract_text_from_docx(file_path: str) -> str:
        return "Texte factice pour test d’upload."
    monkeypatch.setattr("app.routes.documents.extract_text_from_docx", fake_extract_text_from_docx)

# --- TEST UPLOAD DOCUMENT ---
def test_upload_document(client, db_session, mock_extract):
    """
    Vérifie que l'upload d'un .docx crée bien un Document en base.
    """
    data = {
        "file": (io.BytesIO(b"Fake DOCX binary content"), "mon_cours.docx")
    }

    response = client.post("/documents/upload", content_type="multipart/form-data", data=data)
    assert response.status_code == 201

    data = response.get_json()
    doc_id = data["document_id"]
    assert data["title"] == "mon_cours.docx"

    # Vérifie en base
    doc = db_session.get(Document, doc_id)
    assert doc is not None
    assert "Texte factice" in doc.content

    print(f"Document uploadé avec succès : {doc_id}")

# --- TEST SUPPRESSION DOCUMENT ---
def test_delete_document(client, db_session):
    """
    Vérifie que la suppression d'un document efface aussi ses questions.
    """
    # Créer un document + questions associées
    doc_id = str(uuid.uuid4())
    document = Document(id=doc_id, title="Doc à supprimer", content="Texte test")
    db_session.add(document)
    db_session.commit()

    q1 = Question(
        document_id=doc_id,
        type=QuestionType.qcm,
        question="Q1",
        choices=["A", "B", "C", "D"],
        answer="A"
    )
    db_session.add(q1)
    db_session.commit()

    # Vérifie que le document et la question existent
    assert db_session.query(Document).count() == 1
    assert db_session.query(Question).count() == 1

    # Supprimer via l'API
    resp = client.delete(f"/documents/{doc_id}")
    assert resp.status_code == 200

    # Vérifie que tout a été supprimé
    assert db_session.query(Document).count() == 0
    assert db_session.query(Question).count() == 0

    print(f"Document {doc_id} et ses questions supprimés avec succès.")