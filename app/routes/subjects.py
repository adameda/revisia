# app/routes/subjects.py
import uuid
import random
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..db import SessionLocal
from ..models import Subject, Document
from sqlalchemy import func

bp = Blueprint("subjects", __name__, url_prefix="/api/subjects")

# Palette de couleurs harmonieuses pour les matières
COLORS = [
    "#3B82F6",  # Bleu
    "#10B981",  # Vert
    "#F59E0B",  # Orange
    "#EF4444",  # Rouge
    "#8B5CF6",  # Violet
    "#EC4899",  # Rose
    "#14B8A6",  # Turquoise
    "#F97316",  # Orange foncé
    "#6366F1",  # Indigo
    "#84CC16",  # Lime
    "#06B6D4",  # Cyan
    "#D946EF",  # Fuchsia
]


@bp.route("/", methods=["GET"])
@login_required
def get_subjects():
    """
    Récupère toutes les matières de l'utilisateur connecté avec statistiques.
    """
    session = SessionLocal()
    try:
        subjects = session.query(Subject).filter_by(user_id=current_user.id).all()
        
        subjects_data = []
        for subject in subjects:
            # Compter les documents
            doc_count = session.query(Document).filter_by(
                user_id=current_user.id,
                subject_id=subject.id
            ).count()
            
            subjects_data.append({
                "id": subject.id,
                "name": subject.name,
                "color": subject.color,
                "document_count": doc_count,
                "created_at": subject.created_at.isoformat()
            })
        
        session.close()
        return jsonify(subjects_data), 200
        
    except Exception as e:
        session.close()
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@login_required
def create_subject():
    """
    Crée une nouvelle matière pour l'utilisateur connecté.
    """
    data = request.get_json()
    name = data.get("name", "").strip()
    
    if not name:
        return jsonify({"error": "Le nom de la matière est requis"}), 400
    
    session = SessionLocal()
    try:
        # Vérifier si la matière existe déjà (insensible à la casse)
        existing = session.query(Subject).filter(
            Subject.user_id == current_user.id,
            func.lower(Subject.name) == name.lower()
        ).first()
        
        if existing:
            session.close()
            return jsonify({
                "error": "Cette matière existe déjà",
                "existing_id": existing.id
            }), 409
        
        # Choisir une couleur aléatoire
        color = data.get("color", random.choice(COLORS))
        
        subject = Subject(
            id=str(uuid.uuid4()),
            name=name,
            color=color,
            user_id=current_user.id
        )
        
        session.add(subject)
        session.commit()
        
        subject_id = subject.id
        subject_name = subject.name
        subject_color = subject.color
        session.close()
        
        return jsonify({
            "message": "Matière créée avec succès",
            "id": subject_id,
            "name": subject_name,
            "color": subject_color
        }), 201
        
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"error": str(e)}), 500


@bp.route("/<string:subject_id>", methods=["PUT"])
@login_required
def update_subject(subject_id):
    """
    Modifie une matière (nom ou couleur).
    """
    data = request.get_json()
    session = SessionLocal()
    
    try:
        subject = session.get(Subject, subject_id)
        if not subject or subject.user_id != current_user.id:
            session.close()
            return jsonify({"error": "Matière introuvable"}), 404
        
        if "name" in data:
            subject.name = data["name"].strip()
        if "color" in data:
            subject.color = data["color"]
        
        session.commit()
        session.close()
        
        return jsonify({"message": "Matière mise à jour"}), 200
        
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"error": str(e)}), 500


@bp.route("/<string:subject_id>", methods=["DELETE"])
@login_required
def delete_subject(subject_id):
    """
    Supprime une matière uniquement si elle est vide (aucun document associé).
    """
    session = SessionLocal()
    
    try:
        # Vérifier que la matière existe et appartient à l'utilisateur
        subject = session.get(Subject, subject_id)
        if not subject or subject.user_id != current_user.id:
            session.close()
            return jsonify({"error": "Matière introuvable"}), 404
        
        # Vérifier qu'il reste au moins une autre matière
        total_subjects = session.query(Subject).filter_by(user_id=current_user.id).count()
        if total_subjects <= 1:
            session.close()
            return jsonify({"error": "Impossible de supprimer la dernière matière"}), 400
        
        # Vérifier que la matière est vide
        doc_count = session.query(Document).filter_by(
            user_id=current_user.id,
            subject_id=subject_id
        ).count()
        
        if doc_count > 0:
            session.close()
            return jsonify({
                "error": f"Cette matière contient {doc_count} cours. Déplacez ou supprimez les cours d'abord.",
                "document_count": doc_count
            }), 400
        
        # ⚠️ NOUVEAU : Vérifier si la matière est utilisée dans des événements
        from ..models import Event, GroupSubject
        from datetime import datetime
        
        # Événements actifs (en cours)
        now = datetime.now()
        active_events = session.query(Event).filter(
            Event.subject_id == subject_id,
            Event.start_date <= now,
            Event.end_date >= now
        ).count()
        
        if active_events > 0:
            session.close()
            return jsonify({
                "error": f"❌ Impossible : {active_events} événement(s) en cours utilise(nt) cette matière.",
                "active_events": active_events
            }), 400
        
        # Événements futurs (à venir)
        future_events = session.query(Event).filter(
            Event.subject_id == subject_id,
            Event.start_date > now
        ).count()
        
        if future_events > 0:
            session.close()
            return jsonify({
                "error": f"⚠️ Impossible : {future_events} événement(s) à venir utilise(nt) cette matière. Supprimez d'abord les événements.",
                "future_events": future_events
            }), 400
        
        # Vérifier si la matière est liée à des groupes
        group_links = session.query(GroupSubject).filter_by(subject_id=subject_id).count()
        
        if group_links > 0:
            session.close()
            return jsonify({
                "error": f"⚠️ Cette matière est liée à {group_links} groupe(s). Retirez-la des groupes d'abord.",
                "group_links": group_links
            }), 400
        
        # Supprimer la matière (elle est vide et non utilisée)
        session.delete(subject)
        session.commit()
        session.close()
        
        return jsonify({
            "message": "Matière supprimée avec succès"
        }), 200
        
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"error": str(e)}), 500
