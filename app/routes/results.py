import logging
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from ..db import SessionLocal
from ..models import Result, QuizSession, Question
import uuid

# Logger pour tracer les sauvegardes de résultats
logger = logging.getLogger("app.results")

bp = Blueprint("results", __name__, url_prefix="/api/results")


@bp.route("/save", methods=["POST"])
@login_required
def save_results():
    """
    Enregistre les résultats détaillés d'un quiz et crée une session globale (QuizSession).
    Le score et is_correct sont recalculés côté serveur (anti-triche).
    """
    data = request.get_json() or {}
    document_id = data.get("document_id")
    answers = data.get("answers", [])

    if not answers or document_id is None:
        return jsonify({"error": "Données incomplètes"}), 400

    session = SessionLocal()
    try:
        # Récupérer les questions depuis la base pour vérification côté serveur
        question_ids = [a.get("question_id") for a in answers if a.get("question_id")]
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        q_dict = {q.id: q for q in questions}

        # Recalculer le score côté serveur
        score = 0
        verified_answers = []
        for item in answers:
            question_id = item.get("question_id")
            user_answer = item.get("user_answer", "")

            if not question_id or question_id not in q_dict:
                continue

            question = q_dict[question_id]
            is_correct = (
                question.answer is not None
                and user_answer.strip().lower() == question.answer.strip().lower()
            )
            if is_correct:
                score += 1

            verified_answers.append({
                "question_id": question_id,
                "user_answer": user_answer,
                "is_correct": is_correct,
            })

        # Créer la session de quiz globale
        quiz_session = QuizSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            document_id=document_id,
            score=score,
            total_questions=len(verified_answers)
        )
        session.add(quiz_session)
        session.flush()

        # Enregistrer chaque résultat individuel
        for item in verified_answers:
            result = Result(
                id=str(uuid.uuid4()),
                question_id=item["question_id"],
                user_id=current_user.id,
                user_answer=item["user_answer"],
                is_correct=item["is_correct"],
                quiz_session_id=quiz_session.id
            )
            session.add(result)

        session.commit()

        logger.info(f"Résultat enregistré : {current_user.username} - score {score}/{len(verified_answers)} (doc {document_id})")

        return jsonify({
            "message": "Résultats enregistrés ✅",
            "score": score,
            "document_id": document_id,
            "quiz_session_id": quiz_session.id
        }), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur sauvegarde résultat par {current_user.username} : {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()
