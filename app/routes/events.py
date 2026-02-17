"""
Routes pour la gestion des événements/compétitions.
Tout membre d'un groupe peut participer. Seul le propriétaire du groupe peut créer/supprimer.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, func
from datetime import datetime
import random
import json

from ..db import SessionLocal
from ..models import (
    Event, EventQuiz, EventParticipation,
    Group, GroupMember, Subject, Question, GroupSubject, User,
)

events_bp = Blueprint("events", __name__, url_prefix="/events")
logger = logging.getLogger("app.events")


# ============================================
# HELPERS
# ============================================

def _check_group_membership(session, group_id, user_id):
    """Vérifie l'appartenance au groupe. Retourne (group, is_owner, is_member)."""
    group = session.get(Group, group_id)
    if not group:
        return None, False, False
    is_owner = group.owner_id == user_id
    is_member = is_owner or session.query(GroupMember).filter_by(
        group_id=group_id, user_id=user_id
    ).first() is not None
    return group, is_owner, is_member


def _enrich_event_for_user(session, event, user_id):
    """Ajoute des attributs de progression et de statut à un événement."""
    status = event.get_status()
    if status == 'future':
        event.status_label = "À venir"
        event.status_class = "bg-blue-100 text-blue-800"
        event.can_play = False
    elif status == 'ended':
        event.status_label = "Terminé"
        event.status_class = "bg-gray-100 text-gray-800"
        event.can_play = False
    else:
        event.status_label = "En cours"
        event.status_class = "bg-green-100 text-green-800"
        event.can_play = True

    event.participants_count = (
        session.query(EventParticipation.user_id)
        .filter(EventParticipation.event_id == event.id)
        .distinct().count()
    )

    completed = session.query(EventParticipation).filter(
        EventParticipation.event_id == event.id,
        EventParticipation.user_id == user_id,
    ).count()
    event.user_progress = completed
    event.total_quizzes = 5
    event.next_quiz = completed + 1 if completed < 5 else None


# ============================================
# ROUTES
# ============================================

@events_bp.route("/group/<group_id>")
@login_required
def group_events(group_id):
    """Liste des événements d'un groupe."""
    session = SessionLocal()
    try:
        group, is_owner, is_member = _check_group_membership(session, group_id, current_user.id)
        if not group or not is_member:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        events = (
            session.query(Event)
            .filter(Event.group_id == group_id)
            .order_by(Event.start_date.desc())
            .all()
        )
        for event in events:
            _enrich_event_for_user(session, event, current_user.id)

        return render_template("events/list.html", group=group, events=events, is_owner=is_owner)
    finally:
        session.close()


@events_bp.route("/create/<group_id>", methods=["GET", "POST"])
@login_required
def create_event(group_id):
    """Créer un événement (propriétaire du groupe uniquement)."""
    session = SessionLocal()
    try:
        group, is_owner, _ = _check_group_membership(session, group_id, current_user.id)
        if not group or not is_owner:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        group_subjects = (
            session.query(Subject)
            .join(GroupSubject, Subject.id == GroupSubject.subject_id)
            .filter(GroupSubject.group_id == group_id)
            .all()
        )

        if request.method == "POST":
            name = request.form.get("name")
            description = request.form.get("description")
            subject_id = request.form.get("subject_id")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")

            if not all([name, subject_id, start_date_str, end_date_str]):
                flash("Tous les champs obligatoires doivent être remplis.", "error")
                return redirect(request.url)

            if not session.query(GroupSubject).filter(
                and_(GroupSubject.group_id == group_id, GroupSubject.subject_id == subject_id)
            ).first():
                flash("La matière sélectionnée n'est pas liée à ce groupe.", "error")
                return redirect(request.url)

            try:
                start_date = datetime.fromisoformat(start_date_str)
                end_date = datetime.fromisoformat(end_date_str)
                if end_date <= start_date:
                    flash("La date de fin doit être après la date de début.", "error")
                    return redirect(request.url)
            except ValueError:
                flash("Format de date invalide.", "error")
                return redirect(request.url)

            questions = (
                session.query(Question)
                .join(Question.document)
                .filter(Question.document.has(subject_id=subject_id))
                .all()
            )

            required = 100  # 5 quiz × 20 questions
            if len(questions) < required:
                flash(
                    f"❌ La matière ne contient que {len(questions)} question(s), "
                    f"mais {required} sont nécessaires (5 quiz × 20 questions).",
                    "error",
                )
                return render_template("events/create.html", group=group, subjects=group_subjects)

            event = Event(
                name=name,
                description=description,
                group_id=group_id,
                subject_id=subject_id,
                start_date=start_date,
                end_date=end_date,
            )
            session.add(event)
            session.flush()

            all_ids = [q.id for q in questions]
            random.shuffle(all_ids)

            for i in range(1, 6):
                quiz = EventQuiz(
                    event_id=event.id,
                    quiz_number=i,
                    questions=json.dumps(all_ids[(i - 1) * 20 : i * 20]),
                )
                session.add(quiz)

            session.commit()
            logger.info(f"Événement créé : '{name}' dans groupe '{group.name}' par {current_user.username}")
            flash(f"Événement '{name}' créé !", "success")
            return redirect(url_for("events.group_events", group_id=group_id))

        return render_template("events/create.html", group=group, subjects=group_subjects)
    finally:
        session.close()


@events_bp.route("/<event_id>")
@login_required
def event_detail(event_id):
    """Détails d'un événement : classement + progression personnelle."""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            flash("Événement introuvable.", "error")
            return redirect(url_for("ui.home"))

        group, is_owner, is_member = _check_group_membership(session, event.group_id, current_user.id)
        if not is_member:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        # Progression de l'utilisateur
        user_participations = (
            session.query(EventParticipation)
            .filter(EventParticipation.event_id == event_id, EventParticipation.user_id == current_user.id)
            .order_by(EventParticipation.completed_at)
            .all()
        )
        completed_count = len(user_participations)
        next_quiz = completed_count + 1 if completed_count < 5 else None
        user_correct = sum(p.correct_count for p in user_participations)
        user_total_q = sum(p.total_questions for p in user_participations)

        # Classement
        ranking_data = (
            session.query(
                EventParticipation.user_id,
                func.sum(EventParticipation.correct_count).label("total_correct"),
                func.sum(EventParticipation.total_questions).label("total_questions"),
                func.count(EventParticipation.id).label("quiz_count"),
            )
            .filter(EventParticipation.event_id == event_id)
            .group_by(EventParticipation.user_id)
            .all()
        )

        ranking = []
        for user_id, total_correct, total_questions, quiz_count in ranking_data:
            user = session.get(User, user_id)
            ranking.append({
                "user": user,
                "total_correct": total_correct,
                "total_questions": total_questions,
                "quiz_count": quiz_count,
                "is_current_user": user_id == current_user.id,
            })
        ranking.sort(key=lambda x: x["total_correct"], reverse=True)
        for idx, item in enumerate(ranking, 1):
            item["rank"] = idx

        # Stats
        total_participants = len(ranking)
        all_correct = sum(r["total_correct"] for r in ranking)
        all_questions = sum(r["total_questions"] for r in ranking)
        stats = {
            "total_participants": total_participants,
            "total_completions": sum(r["quiz_count"] for r in ranking),
            "avg_correct": round(all_correct / total_participants, 1) if total_participants else 0,
            "avg_total": round(all_questions / total_participants, 1) if total_participants else 0,
            "total_quizzes": 5,
        }

        status = event.get_status()
        can_play = status == "active" and next_quiz is not None

        return render_template(
            "events/detail.html",
            event=event,
            is_owner=is_owner,
            ranking=ranking,
            stats=stats,
            user_participations=user_participations,
            completed_count=completed_count,
            next_quiz=next_quiz,
            user_correct=user_correct,
            user_total_q=user_total_q,
            can_play=can_play,
        )
    finally:
        session.close()


@events_bp.route("/<event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    """Supprimer un événement (propriétaire du groupe uniquement)."""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            flash("Événement introuvable.", "error")
            return redirect(url_for("groups.list_groups"))

        group, is_owner, _ = _check_group_membership(session, event.group_id, current_user.id)
        if not is_owner:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        group_id = event.group_id
        event_name = event.name
        session.delete(event)
        session.commit()
        logger.info(f"Événement supprimé : '{event_name}' par {current_user.username}")
        flash(f"Événement '{event_name}' supprimé.", "success")
        return redirect(url_for("events.group_events", group_id=group_id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("events.group_events", group_id=event.group_id if event else ""))
    finally:
        session.close()


@events_bp.route("/<event_id>/play/<int:quiz_number>")
@login_required
def play_quiz(event_id, quiz_number):
    """Jouer un quiz d'événement."""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            flash("Événement introuvable.", "error")
            return redirect(url_for("ui.home"))

        _, _, is_member = _check_group_membership(session, event.group_id, current_user.id)
        if not is_member:
            flash("❌ Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))

        status = event.get_status()
        if status == "future":
            flash("⚠️ Cet événement n'a pas encore commencé.", "warning")
            return redirect(url_for("events.event_detail", event_id=event_id))
        if status == "ended":
            flash("❌ Cet événement est terminé.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))

        if quiz_number < 1 or quiz_number > 5:
            flash("❌ Numéro de quiz invalide.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))

        quiz = session.query(EventQuiz).filter(
            and_(EventQuiz.event_id == event_id, EventQuiz.quiz_number == quiz_number)
        ).first()
        if not quiz:
            flash("Quiz introuvable.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))

        existing = session.query(EventParticipation).filter(
            EventParticipation.quiz_id == quiz.id,
            EventParticipation.user_id == current_user.id,
        ).first()
        if existing:
            flash("⚠️ Vous avez déjà complété ce quiz.", "warning")
            return redirect(url_for("events.quiz_result", event_id=event_id, participation_id=existing.id))

        completed_count = session.query(EventParticipation).filter(
            EventParticipation.event_id == event_id,
            EventParticipation.user_id == current_user.id,
        ).count()
        expected = completed_count + 1
        if quiz_number != expected:
            flash(f"🔒 Vous devez d'abord compléter le Quiz {expected}.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))

        question_ids = json.loads(quiz.questions)
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        q_dict = {q.id: q for q in questions}
        questions_ordered = [q_dict[qid] for qid in question_ids if qid in q_dict]

        return render_template("events/play.html", event=event, quiz=quiz, questions=questions_ordered)
    finally:
        session.close()


@events_bp.route("/<event_id>/submit/<int:quiz_number>", methods=["POST"])
@login_required
def submit_quiz(event_id, quiz_number):
    """Soumettre les réponses d'un quiz d'événement."""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            return jsonify({"error": "Événement introuvable"}), 404

        _, _, is_member = _check_group_membership(session, event.group_id, current_user.id)
        if not is_member:
            return jsonify({"error": "Accès non autorisé"}), 403

        if event.get_status() != "active":
            return jsonify({"error": "Événement non actif"}), 403

        if quiz_number < 1 or quiz_number > 5:
            return jsonify({"error": "Numéro de quiz invalide"}), 400

        quiz = session.query(EventQuiz).filter(
            and_(EventQuiz.event_id == event_id, EventQuiz.quiz_number == quiz_number)
        ).first()
        if not quiz:
            return jsonify({"error": "Quiz introuvable"}), 404

        if session.query(EventParticipation).filter(
            EventParticipation.quiz_id == quiz.id,
            EventParticipation.user_id == current_user.id,
        ).first():
            return jsonify({"error": "Quiz déjà complété"}), 400

        completed_count = session.query(EventParticipation).filter(
            EventParticipation.event_id == event_id,
            EventParticipation.user_id == current_user.id,
        ).count()
        if quiz_number != completed_count + 1:
            return jsonify({"error": f"Complétez le Quiz {completed_count + 1} d'abord"}), 403

        data = request.get_json()
        answers = data.get("answers", {})
        time_spent = data.get("time_spent", 0)

        question_ids = json.loads(quiz.questions)
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        q_dict = {q.id: q for q in questions}

        correct_count = 0
        detailed_answers = []
        for qid in question_ids:
            if qid not in q_dict:
                continue
            question = q_dict[qid]
            user_answer = answers.get(qid, "")
            is_correct = question.type.value == "qcm" and user_answer.strip().lower() == question.answer.strip().lower()
            if is_correct:
                correct_count += 1
            detailed_answers.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": question.answer,
                "is_correct": is_correct,
            })

        participation = EventParticipation(
            event_id=event_id,
            quiz_id=quiz.id,
            user_id=current_user.id,
            correct_count=correct_count,
            total_questions=len(question_ids),
            time_spent=time_spent,
            answers=json.dumps(detailed_answers),
        )
        session.add(participation)
        session.commit()

        logger.info(f"Participation : {current_user.username} - quiz {quiz_number} - {correct_count}/{len(question_ids)} ({time_spent}s)")

        return jsonify({
            "success": True,
            "correct": correct_count,
            "total": len(question_ids),
            "redirect": url_for("events.quiz_result", event_id=event_id, participation_id=participation.id),
        })
    finally:
        session.close()


@events_bp.route("/<event_id>/result/<participation_id>")
@login_required
def quiz_result(event_id, participation_id):
    """Résultat d'un quiz complété."""
    session = SessionLocal()
    try:
        participation = session.get(EventParticipation, participation_id)
        if not participation or participation.user_id != current_user.id:
            flash("Résultat introuvable.", "error")
            return redirect(url_for("ui.home"))

        event = session.get(Event, event_id)
        quiz = session.get(EventQuiz, participation.quiz_id)

        detailed_answers = json.loads(participation.answers)
        q_ids = [a["question_id"] for a in detailed_answers]
        questions = session.query(Question).filter(Question.id.in_(q_ids)).all()
        q_dict = {q.id: q for q in questions}

        for answer in detailed_answers:
            qid = answer["question_id"]
            if qid in q_dict:
                answer["question"] = q_dict[qid]

        completed_count = session.query(EventParticipation).filter(
            EventParticipation.event_id == event_id,
            EventParticipation.user_id == current_user.id,
        ).count()
        next_quiz = completed_count + 1 if completed_count < 5 else None

        return render_template(
            "events/result.html",
            event=event,
            quiz=quiz,
            participation=participation,
            detailed_answers=detailed_answers,
            next_quiz=next_quiz,
        )
    finally:
        session.close()
