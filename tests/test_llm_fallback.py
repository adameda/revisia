# tests/test_llm_fallback.py
"""
Tests automatisés pour le système de fallback multi-clés Gemini
et la gestion d'erreurs dans llm.py.

Lance avec : python -m pytest tests/test_llm_fallback.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from app.llm import generate_quiz_from_text, QuizResponse, QuizItem

# Tous les tests de ce fichier n'ont pas besoin de DB
pytestmark = pytest.mark.no_db


# === Helpers ===

SAMPLE_TEXT = """
La Révolution française est un événement majeur de l'histoire de France.
Elle débute en 1789 avec la prise de la Bastille et se termine en 1799.
Les causes principales sont la crise financière, les inégalités sociales
et l'influence des philosophes des Lumières comme Voltaire et Rousseau.
La Déclaration des droits de l'homme et du citoyen est adoptée le 26 août 1789.
"""


def make_valid_response(n=5):
    """Crée une réponse Gemini valide simulée (texte JSON parsable par QuizResponse)."""
    items = []
    for i in range(n):
        items.append({
            "type": "qcm",
            "question": f"Question test {i+1} ?",
            "choices": [f"Choix A{i}", f"Choix B{i}", f"Choix C{i}", f"Choix D{i}"],
            "answer": f"Choix A{i}",
        })
    import json
    return json.dumps({"items": items})


def make_client_success(n=5):
    """Crée un faux client Gemini qui retourne une réponse valide."""
    client = MagicMock()
    response = MagicMock()
    response.text = make_valid_response(n)
    client.models.generate_content.return_value = response
    return client


def make_client_quota_error():
    """Crée un faux client qui lève une erreur quota (ResourceExhausted / 429)."""
    client = MagicMock()
    client.models.generate_content.side_effect = Exception(
        "429 Resource has been exhausted (e.g. check quota)."
    )
    return client


def make_client_generic_error():
    """Crée un faux client qui lève une erreur générique (pas quota)."""
    client = MagicMock()
    client.models.generate_content.side_effect = Exception(
        "Invalid API key provided"
    )
    return client


# === Tests ===

class TestAppelNormal:
    """La clé 1 fonctionne du premier coup."""

    def test_first_key_works(self):
        call_keys = []

        def mock_client(api_key):
            call_keys.append(api_key)
            return make_client_success(5)

        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", ["real_key_1", "real_key_2"]), \
             patch("app.llm.genai.Client", side_effect=mock_client):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 5)

        assert error is None
        assert len(questions) == 5
        assert call_keys == ["real_key_1"]  # Seule clé 1 utilisée
        # Vérifier la structure des questions
        for q in questions:
            assert "type" in q
            assert "question" in q
            assert "choices" in q
            assert "answer" in q
            assert q["type"] == "qcm"
            assert len(q["choices"]) == 4


class TestFallbackCle2:
    """Clé 1 quota exhausted → bascule sur clé 2."""

    def test_fallback_on_quota_exceeded(self):
        call_keys = []

        def mock_client(api_key):
            call_keys.append(api_key)
            if api_key == "fake_key_1":
                return make_client_quota_error()
            return make_client_success(5)

        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", ["fake_key_1", "real_key_2"]), \
             patch("app.llm.genai.Client", side_effect=mock_client):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 5)

        assert error is None
        assert len(questions) == 5
        assert call_keys == ["fake_key_1", "real_key_2"]  # Les 2 clés ont été tentées


class TestToutesClesQuotaEpuise:
    """Les 2 clés retournent quota exhausted → error quota_exceeded."""

    def test_all_keys_quota_exhausted(self):
        call_keys = []

        def mock_client(api_key):
            call_keys.append(api_key)
            return make_client_quota_error()

        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", ["fake_key_1", "fake_key_2"]), \
             patch("app.llm.genai.Client", side_effect=mock_client):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 5)

        assert questions == []
        assert error == "quota_exceeded"
        assert call_keys == ["fake_key_1", "fake_key_2"]  # Les 2 ont été tentées


class TestErreurGenerique:
    """Erreur non-quota (ex: clé invalide) → retourne immédiatement 'error'."""

    def test_generic_error_no_fallback(self):
        call_keys = []

        def mock_client(api_key):
            call_keys.append(api_key)
            return make_client_generic_error()

        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", ["bad_key_1", "good_key_2"]), \
             patch("app.llm.genai.Client", side_effect=mock_client):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 5)

        assert questions == []
        assert error == "error"
        # Erreur générique : pas de fallback, s'arrête à la 1ère clé
        assert call_keys == ["bad_key_1"]


class TestAucuneCle:
    """Aucune clé API configurée → retourne 'error'."""

    def test_no_api_keys(self):
        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", []):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 5)

        assert questions == []
        assert error == "error"


class TestModeMock:
    """Le mode mock retourne des questions sans appel API."""

    def test_mock_mode_returns_questions(self):
        with patch("app.llm.MOCK_MODE", True):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 10)

        assert error is None
        assert len(questions) == 10
        for q in questions:
            assert q["type"] == "qcm"
            assert len(q["choices"]) == 4
            assert "answer" in q

    def test_mock_mode_no_api_call(self):
        """Vérifie qu'aucun appel réseau n'est fait en mode mock."""
        with patch("app.llm.MOCK_MODE", True), \
             patch("app.llm.genai.Client") as mock_genai:
            generate_quiz_from_text(SAMPLE_TEXT, 5)

        mock_genai.assert_not_called()


class TestStructureQuestions:
    """Vérifie que le parsing de la réponse Gemini produit le bon format."""

    def test_question_format(self):
        def mock_client(api_key):
            return make_client_success(3)

        with patch("app.llm.MOCK_MODE", False), \
             patch("app.llm.API_KEYS", ["key_1"]), \
             patch("app.llm.genai.Client", side_effect=mock_client):
            questions, error = generate_quiz_from_text(SAMPLE_TEXT, 3)

        assert error is None
        assert len(questions) == 3
        for q in questions:
            assert isinstance(q["question"], str)
            assert isinstance(q["choices"], list)
            assert isinstance(q["answer"], str)
            assert q["answer"] in q["choices"]
