# app/routes/ui.py
from flask import Blueprint, render_template, jsonify, request
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user
from ..db import SessionLocal
from ..models import Document, Question, QuizSession, Subject
from sqlalchemy import func
import os

bp = Blueprint("ui", __name__)

def get_empty_message(current_filter, subjects_with_stats):
    """Génère le message approprié quand il n'y a aucun document"""
    if not current_filter or current_filter == "all":
        return {
            'title': 'Aucun cours pour le moment.',
            'action_text': 'Ajouter votre premier cours',
            'action_url': '/upload'
        }
    
    # Trouver le nom de la matière filtrée
    subject_name = None
    for subject in subjects_with_stats:
        if subject['id'] == current_filter:
            subject_name = subject['name']
            break
    
    if subject_name:
        return {
            'title': f'Aucun cours dans {subject_name} pour le moment.',
            'action_text': f'Ajouter un cours dans cette matière',
            'action_url': f'/upload?subject={current_filter}'
        }
    else:
        return {
            'title': 'Aucun cours pour le moment.',
            'action_text': 'Ajouter votre premier cours',
            'action_url': '/upload'
        }

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/documents")
@login_required
def show_documents():
    from ..extract import count_words, get_preview
    
    # Récupérer le filtre de matière depuis l'URL
    subject_filter = request.args.get("subject")  # Peut être None, "all", ou un subject_id
    
    with SessionLocal() as session:
        # Charger les matières avec leurs stats
        subjects = session.query(Subject).filter_by(user_id=current_user.id).all()
        subjects_with_stats = []
        
        for subject in subjects:
            doc_count = session.query(Document).filter_by(
                user_id=current_user.id,
                subject_id=subject.id
            ).count()
            
            subjects_with_stats.append({
                'id': subject.id,
                'name': subject.name,
                'color': subject.color,
                'doc_count': doc_count
            })
        
        # Compter le total de documents
        total_docs = session.query(Document).filter_by(user_id=current_user.id).count()
        
        # Construire la requête des documents
        query = (
            session.query(Document)
            .options(joinedload(Document.questions), joinedload(Document.subject))
            .filter_by(user_id=current_user.id)
        )
        
        # Appliquer le filtre si nécessaire
        if subject_filter and subject_filter != "all":
            query = query.filter_by(subject_id=subject_filter)
        
        docs = query.order_by(Document.created_at.desc()).all()
        
        # Ajouter les métadonnées pour chaque document
        docs_with_meta = []
        for doc in docs:
            doc_dict = {
                'id': doc.id,
                'title': doc.title,
                'content': doc.content,
                'created_at': doc.created_at,
                'questions': list(doc.questions),
                'word_count': count_words(doc.content),
                'preview': get_preview(doc.content, max_chars=150),
                'subject': {
                    'id': doc.subject.id,
                    'name': doc.subject.name,
                    'color': doc.subject.color
                } if doc.subject else None
            }
            docs_with_meta.append(doc_dict)
        
        # Générer le message pour liste vide
        empty_message = None if docs_with_meta else get_empty_message(subject_filter, subjects_with_stats)
        
        # Trouver la matière sélectionnée
        selected_subject = None
        if subject_filter and subject_filter != "all":
            for subject in subjects_with_stats:
                if subject['id'] == subject_filter:
                    selected_subject = subject
                    break

    return render_template(
        "documents.html", 
        documents=docs_with_meta, 
        subjects=subjects_with_stats,
        current_filter=subject_filter or "all",
        total_docs=total_docs,
        empty_message=empty_message,
        selected_subject=selected_subject,
        mock_mode=os.getenv("MOCK_GEMINI") == "True"
    )

@bp.route("/upload")
@login_required
def upload():
    # Récupérer l'ID de la matière si passée en paramètre
    preselected_subject = request.args.get("subject", "")
    
    with SessionLocal() as session:
        # Charger les matières de l'utilisateur
        subjects = session.query(Subject).filter_by(user_id=current_user.id).all()
        subjects_list = [{'id': s.id, 'name': s.name, 'color': s.color} for s in subjects]
    
    return render_template(
        "upload.html", 
        subjects=subjects_list,
        preselected_subject=preselected_subject
    )

@bp.route("/quizzes/<string:document_id>")
@login_required
def show_quiz(document_id):
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if not document:
            return render_template("404.html", message="Document introuvable"), 404
        questions = session.query(Question).filter_by(document_id=document_id).all()

    return render_template("quiz.html", quiz_title=document.title, questions=questions)

@bp.route("/quizzes/play/<string:document_id>")
@login_required
def play_quiz(document_id):
    from random import sample
    session = SessionLocal()

    document = session.get(Document, document_id)
    if not document:
        session.close()
        return render_template("404.html", message="Document introuvable"), 404

    questions = session.query(Question).filter_by(document_id=document_id).all()
    session.close()

    if not questions:
        return render_template(
            "quiz_play.html",
            title=document.title,
            document=document,
            questions=[],
            message="Aucune question générée pour ce document."
        )

    if len(questions) > 10:
        questions = sample(questions, 10)

    # Convertir les questions en dictionnaires simples
    questions_data = [
        {
            "id": q.id,
            "question": q.question,
            "type": q.type.value if hasattr(q.type, "value") else q.type,
            "choices": q.choices,
            "answer": q.answer,
            "explanation": q.explanation
        }
        for q in questions
    ]

    return render_template(
        "quiz_play.html",
        title=document.title,
        document=document,
        questions=questions_data
    )

@bp.route("/results")
@login_required
def show_results():
    """
    Page HTML de visualisation des résultats (graphique)
    """
    with SessionLocal() as session:
        documents = (
            session.query(Document)
            .filter_by(user_id=current_user.id)
            .order_by(Document.created_at.desc())
            .all()
        )

    return render_template("results.html", documents=documents)


@bp.route("/api/results/data", methods=["GET"])
@login_required
def get_results_data():
    """
    API pour renvoyer les données de score par document (pour le graphique)
    """
    document_id = request.args.get("document_id")
    if not document_id:
        return jsonify({"error": "document_id manquant"}), 400

    with SessionLocal() as session:
        sessions = (
            session.query(QuizSession)
            .filter_by(user_id=current_user.id, document_id=document_id)
            .order_by(QuizSession.played_at.asc())
            .all()
        )

    data = [
        {
            "played_at": s.played_at.strftime("%Y-%m-%d %H:%M"),
            "score": s.score
        }
        for s in sessions
    ]

    return jsonify(data)

