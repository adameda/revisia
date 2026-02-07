# app/routes/quizzes.py
from flask import Blueprint, request, jsonify
from ..db import SessionLocal
from ..models import Document, Question, QuestionType
from ..llm import generate_quiz_from_text
import uuid

bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")

def calculate_questions_count(word_count: int) -> int:
    """
    Calcule le nombre de questions optimal basé sur le nombre de mots.
    - < 800 mots : 20 questions (Petit cours)
    - 800-1500 mots : 30 questions (Moyen cours)
    - > 1500 mots : 40 questions (Grand cours)
    """
    if word_count < 800:
        return 20
    elif word_count <= 1500:
        return 30
    else:
        return 40

@bp.route("/generate", methods=["POST"])
def generate_quiz():
    document_id = request.args.get("document_id")
    if not document_id:
        return jsonify({"error": "Paramètre 'document_id' requis"}), 400

    session = SessionLocal()
    try:
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

        questions = generate_quiz_from_text(document.content, total_questions=total_questions)
        if not questions:
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
        session.commit()

        return jsonify({
            "message": f"{len(questions)} questions générées",
            "total_questions": len(questions),
            "word_count": word_count
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()