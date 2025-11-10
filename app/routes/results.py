from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from ..db import SessionLocal
from ..models import Result, QuizSession
import uuid

bp = Blueprint("results", __name__, url_prefix="/api/results")


@bp.route("/save", methods=["POST"])
@login_required
def save_results():
    """
    Enregistre les résultats détaillés d’un quiz et crée une session globale (QuizSession)
    """
    data = request.get_json() or {}
    document_id = data.get("document_id")
    answers = data.get("answers", [])
    score = data.get("score")

    if not answers or document_id is None or score is None:
        return jsonify({"error": "Données incomplètes"}), 400

    session = SessionLocal()
    try:
        # Créer la session de quiz globale
        quiz_session = QuizSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            document_id=document_id,
            score=score,
            total_questions=len(answers)
        )
        session.add(quiz_session)
        session.flush()  # pour obtenir l'ID avant d'ajouter les résultats

        # Enregistrer chaque résultat individuel
        for item in answers:
            question_id = item.get("question_id")
            user_answer = item.get("user_answer", "")
            is_correct = item.get("is_correct", False)

            if not question_id:
                continue

            result = Result(
                id=str(uuid.uuid4()),
                question_id=question_id,
                user_id=current_user.id,
                user_answer=user_answer,
                is_correct=is_correct,
                quiz_session_id=quiz_session.id
            )
            session.add(result)

        session.commit()

        return jsonify({
            "message": "Résultats enregistrés ✅",
            "score": score,
            "document_id": document_id,
            "quiz_session_id": quiz_session.id
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()