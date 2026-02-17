# app/routes/quizzes.py
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, time
from ..db import SessionLocal
from ..models import Document, Question, QuestionType, QuizGeneration
from ..llm import generate_quiz_from_text
import uuid

bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")
logger = logging.getLogger("app.quizzes")

# Rate limiter pour éviter l'abus de génération (appels API Gemini coûteux)
from ..extensions import limiter

def calculate_questions_count(word_count: int) -> int:
    """
    Calcule le nombre de questions optimal basé sur le nombre de mots.
    - < 800 mots : 30 questions (Petit cours)
    - 800-1500 mots : 40 questions (Moyen cours)
    - > 1500 mots : 50 questions (Grand cours)
    """
    if word_count < 800:
        return 30
    elif word_count <= 1500:
        return 40
    else:
        return 50

# Limite : 10 requêtes/minute par IP (en plus de la limite quotidienne par user)
@bp.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def generate_quiz():
    document_id = request.args.get("document_id")
    if not document_id:
        return jsonify({"error": "Paramètre 'document_id' requis"}), 400

    session = SessionLocal()
    try:
        # Appliquer la limite seulement si activée
        quiz_limit_enabled = current_app.config.get("QUIZ_LIMIT_ENABLED", False)
        daily_limit = current_app.config.get("DAILY_QUIZ_LIMIT", 10)
        today_start = datetime.combine(datetime.now().date(), time.min)
        daily_count = session.query(QuizGeneration).filter(
            QuizGeneration.user_id == current_user.id,
            QuizGeneration.created_at >= today_start
        ).count()

        if quiz_limit_enabled and daily_count >= daily_limit:
            remaining = 0
            logger.warning(f"Quota atteint : {current_user.username} ({daily_limit}/{daily_limit})")
            return jsonify({
                "error": f"Limite atteinte ({daily_limit}/{daily_limit} aujourd'hui). Reviens demain !",
                "quota_remaining": remaining,
            }), 429

        document = session.get(Document, document_id)
        if not document:
            return jsonify({"error": "Document introuvable"}), 404

        existing = session.query(Question).filter_by(document_id=document_id).first()
        if existing:
            return jsonify({"message": "Quiz déjà généré pour ce document"}), 200

        # Détection automatique du nombre de questions
        from ..extract import count_words
        word_count = count_words(document.content)
        total_questions = calculate_questions_count(word_count)

        questions, error = generate_quiz_from_text(document.content, total_questions=total_questions)

        if error == "quota_exceeded":
            logger.warning(f"API Gemini indisponible (toutes clés épuisées) pour {current_user.username}")
            return jsonify({"error": "Service temporairement indisponible. Réessaie plus tard."}), 503
        elif error == "error":
            logger.error(f"Erreur génération quiz pour {current_user.username}")
            return jsonify({"error": "Erreur lors de la génération. Réessaie."}), 500
        elif not questions:
            return jsonify({"error": "Aucune question générée"}), 500

        for q in questions:
            question = Question(
                id=str(uuid.uuid4()),
                document_id=document_id,
                type=QuestionType.qcm if q["type"] == "qcm" else QuestionType.ouverte,
                question=q["question"],
                choices=q.get("choices"),
                answer=q.get("answer"),
                explanation=q.get("explanation"),
            )
            session.add(question)

        # Enregistrer la génération dans le compteur
        session.add(QuizGeneration(user_id=current_user.id))
        session.commit()

        quota_remaining = max(0, daily_limit - daily_count - 1)

        logger.info(f"Quiz généré : {len(questions)} questions pour '{document.title}' par {current_user.username} (reste {quota_remaining})")

        return jsonify({
            "message": f"{len(questions)} questions générées",
            "total_questions": len(questions),
            "word_count": word_count,
            "quota_remaining": quota_remaining,
        }), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur inattendue génération quiz : {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()