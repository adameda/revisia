"""
Routes pour la gestion des événements/compétitions
Permet aux professeurs de créer des événements et aux étudiants d'y participer
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
import random
import json

from ..db import SessionLocal
from ..models import Event, EventQuiz, EventParticipation, Group, GroupMember, Subject, Question, GroupSubject

# Blueprint pour les professeurs
teacher_events_bp = Blueprint('teacher_events', __name__, url_prefix='/teacher/events')

# Blueprint pour les étudiants
student_events_bp = Blueprint('student_events', __name__, url_prefix='/events')


# ========== ROUTES PROFESSEUR ==========

@teacher_events_bp.route('/group/<group_id>')
@login_required
def group_events(group_id):
    """Liste des événements d'un groupe (vue professeur)"""
    if not current_user.is_teacher:
        flash("Accès refusé. Vous devez être professeur.", "error")
        return redirect(url_for('ui.home'))
    
    session = SessionLocal()
    try:
        group = session.get(Group, group_id)
        if not group or group.teacher_id != current_user.id:
            flash("Groupe introuvable ou accès non autorisé.", "error")
            return redirect(url_for('teacher.list_groups'))
        
        # Récupérer tous les événements du groupe
        events = session.query(Event).filter(
            Event.group_id == group_id
        ).order_by(Event.start_date.desc()).all()
        
        # Enrichir avec des stats
        for event in events:
            # Nombre de participants uniques
            event.participants_count = session.query(EventParticipation.user_id).filter(
                EventParticipation.event_id == event.id
            ).distinct().count()
            
            # ⚠️ Statut de l'événement (clôture automatique)
            status = event.get_status()
            if status == 'future':
                event.status = "À venir"
                event.status_class = "bg-blue-100 text-blue-800"
            elif status == 'ended':
                event.status = "Terminé"
                event.status_class = "bg-gray-100 text-gray-800"
            else:  # active
                event.status = "En cours"
                event.status_class = "bg-green-100 text-green-800"
        
        return render_template('teacher/events.html', group=group, events=events)
    finally:
        session.close()


@teacher_events_bp.route('/create/<group_id>', methods=['GET', 'POST'])
@login_required
def create_event(group_id):
    """Créer un événement pour un groupe"""
    if not current_user.is_teacher:
        flash("Accès refusé. Vous devez être professeur.", "error")
        return redirect(url_for('ui.home'))
    
    session = SessionLocal()
    try:
        group = session.get(Group, group_id)
        if not group or group.teacher_id != current_user.id:
            flash("Groupe introuvable ou accès non autorisé.", "error")
            return redirect(url_for('teacher.list_groups'))
        
        # Récupérer les matières liées au groupe
        group_subjects = session.query(Subject).join(
            GroupSubject, Subject.id == GroupSubject.subject_id
        ).filter(GroupSubject.group_id == group_id).all()
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            subject_id = request.form.get('subject_id')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            # Validation
            if not all([name, subject_id, start_date_str, end_date_str]):
                flash("Tous les champs obligatoires doivent être remplis.", "error")
                return redirect(request.url)
            
            # Vérifier que la matière est bien liée au groupe
            subject_in_group = session.query(GroupSubject).filter(
                and_(GroupSubject.group_id == group_id, GroupSubject.subject_id == subject_id)
            ).first()
            
            if not subject_in_group:
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
            
            # Récupérer toutes les questions de la matière
            questions = session.query(Question).join(
                Question.document
            ).filter(Question.document.has(subject_id=subject_id)).all()
            
            # ⚠️ VALIDATION CRITIQUE : Vérifier le nombre de questions
            required_questions = 100  # 5 quiz x 20 questions
            if len(questions) < required_questions:
                flash(f"❌ Impossible de créer l'événement : la matière ne contient que {len(questions)} question(s), mais {required_questions} sont nécessaires (5 quiz × 20 questions).", "error")
                return render_template('teacher/event_create.html', group=group, subjects=group_subjects)
            
            # Créer l'événement
            event = Event(
                name=name,
                description=description,
                group_id=group_id,
                subject_id=subject_id,
                start_date=start_date,
                end_date=end_date
            )
            session.add(event)
            session.flush()  # Pour obtenir l'ID de l'événement
            
            # Générer les 5 quiz avec 20 questions aléatoires chacun
            all_question_ids = [q.id for q in questions]
            random.shuffle(all_question_ids)
            
            for i in range(1, 6):  # Quiz 1 à 5
                start_idx = (i - 1) * 20
                end_idx = start_idx + 20
                quiz_questions = all_question_ids[start_idx:end_idx]
                
                quiz = EventQuiz(
                    event_id=event.id,
                    quiz_number=i,
                    questions=json.dumps(quiz_questions)
                )
                session.add(quiz)
            
            session.commit()
            flash(f"Événement '{name}' créé avec succès !", "success")
            return redirect(url_for('teacher_events.group_events', group_id=group_id))
        
        return render_template('teacher/event_create.html', group=group, subjects=group_subjects)
    finally:
        session.close()


@teacher_events_bp.route('/<event_id>')
@login_required
def event_detail(event_id):
    """Détails d'un événement avec classement et statistiques"""
    if not current_user.is_teacher:
        flash("Accès refusé. Vous devez être professeur.", "error")
        return redirect(url_for('ui.home'))
    
    session = SessionLocal()
    try:
        from sqlalchemy import func
        event = session.get(Event, event_id)
        if not event or event.group.teacher_id != current_user.id:
            flash("Événement introuvable ou accès non autorisé.", "error")
            return redirect(url_for('teacher.list_groups'))
        
        # Calculer le classement
        # Pour chaque étudiant : score total, nombre de quiz complétés
        ranking_data = session.query(
            EventParticipation.user_id,
            func.sum(EventParticipation.score).label('total_score'),
            func.count(EventParticipation.id).label('quiz_count')
        ).filter(
            EventParticipation.event_id == event_id
        ).group_by(EventParticipation.user_id).all()
        
        # Enrichir avec les infos utilisateur
        from ..models import User
        ranking = []
        for user_id, total_score, quiz_count in ranking_data:
            user = session.get(User, user_id)
            ranking.append({
                'user': user,
                'total_score': total_score,
                'quiz_count': quiz_count,
                'avg_score': round(total_score / quiz_count, 1) if quiz_count > 0 else 0
            })
        
        # Trier par score total décroissant
        ranking.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Ajouter le rang
        for idx, item in enumerate(ranking, 1):
            item['rank'] = idx
        
        # Statistiques globales
        total_participants = len(ranking)
        total_completions = sum(r['quiz_count'] for r in ranking)
        avg_score = round(sum(r['total_score'] for r in ranking) / total_participants, 1) if total_participants > 0 else 0
        
        stats = {
            'total_participants': total_participants,
            'total_completions': total_completions,
            'avg_score': avg_score,
            'total_quizzes': 5
        }
        
        return render_template('teacher/event_detail.html', event=event, ranking=ranking, stats=stats)
    finally:
        session.close()


@teacher_events_bp.route('/<event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """Supprimer un événement"""
    if not current_user.is_teacher:
        return jsonify({'error': 'Accès refusé'}), 403
    
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event or event.group.teacher_id != current_user.id:
            return jsonify({'error': 'Événement introuvable'}), 404
        
        # ⚠️ Vérifier s'il y a des participations
        participation_count = session.query(EventParticipation).filter_by(event_id=event_id).count()
        
        if participation_count > 0:
            # Il y a des participations, on avertit mais on permet la suppression
            flash(f"⚠️ Attention : {participation_count} participation(s) seront supprimées avec cet événement.", "warning")
        
        group_id = event.group_id
        event_name = event.name
        
        # La cascade DELETE se chargera de supprimer les quiz et participations
        session.delete(event)
        session.commit()
        
        flash(f"✅ Événement '{event_name}' supprimé avec succès.", "success")
        return redirect(url_for('teacher_events.group_events', group_id=group_id))
    except Exception as e:
        session.rollback()
        flash(f"❌ Erreur lors de la suppression : {str(e)}", "error")
        return redirect(url_for('teacher_events.group_events', group_id=event.group_id if event else ''))
    finally:
        session.close()


# ========== ROUTES ÉTUDIANT ==========

@student_events_bp.route('/group/<group_id>')
@login_required
def group_events(group_id):
    """Liste des événements d'un groupe (vue étudiant)"""
    session = SessionLocal()
    try:
        # Vérifier que l'étudiant est membre du groupe
        membership = session.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id)
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for('groups.list_groups'))
        
        group = session.get(Group, group_id)
        
        # Récupérer les événements actifs ou à venir
        now = datetime.now()
        events = session.query(Event).filter(
            and_(Event.group_id == group_id, Event.end_date >= now)
        ).order_by(Event.start_date).all()
        
        # Pour chaque événement, calculer la progression de l'utilisateur
        for event in events:
            # Nombre de quiz complétés par l'utilisateur
            completed_quizzes = session.query(EventParticipation).filter(
                and_(
                    EventParticipation.event_id == event.id,
                    EventParticipation.user_id == current_user.id
                )
            ).count()
            
            event.user_progress = completed_quizzes
            event.total_quizzes = 5
            event.next_quiz = completed_quizzes + 1 if completed_quizzes < 5 else None
            
            # Statut
            if now < event.start_date:
                event.status = "À venir"
                event.status_class = "bg-blue-100 text-blue-800"
                event.can_play = False
            elif now > event.end_date:
                event.status = "Terminé"
                event.status_class = "bg-gray-100 text-gray-800"
                event.can_play = False
            else:
                event.status = "En cours"
                event.status_class = "bg-green-100 text-green-800"
                event.can_play = True
        
        return render_template('student/events.html', group=group, events=events)
    finally:
        session.close()


@student_events_bp.route('/<event_id>')
@login_required
def event_detail(event_id):
    """Détails d'un événement avec classement et progression personnelle"""
    session = SessionLocal()
    try:
        from sqlalchemy import func
        event = session.get(Event, event_id)
        if not event:
            flash("Événement introuvable.", "error")
            return redirect(url_for('ui.home'))
        
        # Vérifier que l'étudiant est membre du groupe
        membership = session.query(GroupMember).filter(
            and_(GroupMember.group_id == event.group_id, GroupMember.user_id == current_user.id)
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for('ui.home'))
        
        # Progression de l'utilisateur
        user_participations = session.query(EventParticipation).filter(
            and_(
                EventParticipation.event_id == event_id,
                EventParticipation.user_id == current_user.id
            )
        ).order_by(EventParticipation.completed_at).all()
        
        completed_count = len(user_participations)
        next_quiz = completed_count + 1 if completed_count < 5 else None
        user_total_score = sum(p.score for p in user_participations)
        
        # Classement général
        ranking_data = session.query(
            EventParticipation.user_id,
            func.sum(EventParticipation.score).label('total_score'),
            func.count(EventParticipation.id).label('quiz_count')
        ).filter(
            EventParticipation.event_id == event_id
        ).group_by(EventParticipation.user_id).all()
        
        from ..models import User
        ranking = []
        for user_id, total_score, quiz_count in ranking_data:
            user = session.get(User, user_id)
            ranking.append({
                'user': user,
                'total_score': total_score,
                'quiz_count': quiz_count,
                'is_current_user': user_id == current_user.id
            })
        
        ranking.sort(key=lambda x: x['total_score'], reverse=True)
        
        for idx, item in enumerate(ranking, 1):
            item['rank'] = idx
        
        # ⚠️ Vérifier si l'événement est actif (clôture automatique)
        status = event.get_status()
        can_play = status == 'active' and next_quiz is not None
        
        return render_template('student/event_detail.html', 
                              event=event, 
                              ranking=ranking,
                              user_participations=user_participations,
                              completed_count=completed_count,
                              next_quiz=next_quiz,
                              user_total_score=user_total_score,
                              can_play=can_play)
    finally:
        session.close()


@student_events_bp.route('/<event_id>/play/<int:quiz_number>')
@login_required
def play_quiz(event_id, quiz_number):
    """Jouer un quiz d'événement"""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            flash("Événement introuvable.", "error")
            return redirect(url_for('ui.home'))
        
        # ⚠️ VÉRIFICATION 1 : Membership du groupe
        membership = session.query(GroupMember).filter(
            and_(GroupMember.group_id == event.group_id, GroupMember.user_id == current_user.id)
        ).first()
        
        if not membership:
            flash("❌ Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for('groups.list_groups'))
        
        # ⚠️ VÉRIFICATION 2 : Événement actif (clôture automatique)
        event_status = event.get_status()
        if event_status == 'future':
            flash("⚠️ Cet événement n'a pas encore commencé.", "warning")
            return redirect(url_for('student_events.event_detail', event_id=event_id))
        elif event_status == 'ended':
            flash("❌ Cet événement est terminé.", "error")
            return redirect(url_for('student_events.event_detail', event_id=event_id))
        
        # ⚠️ VÉRIFICATION 3 : Quiz existe
        if quiz_number < 1 or quiz_number > 5:
            flash("❌ Numéro de quiz invalide.", "error")
            return redirect(url_for('student_events.event_detail', event_id=event_id))
        
        quiz = session.query(EventQuiz).filter(
            and_(EventQuiz.event_id == event_id, EventQuiz.quiz_number == quiz_number)
        ).first()
        
        if not quiz:
            flash("Quiz introuvable.", "error")
            return redirect(url_for('student_events.event_detail', event_id=event_id))
        
        # ⚠️ VÉRIFICATION 4 : Pas déjà complété
        existing_participation = session.query(EventParticipation).filter(
            and_(
                EventParticipation.quiz_id == quiz.id,
                EventParticipation.user_id == current_user.id
            )
        ).first()
        
        if existing_participation:
            flash("⚠️ Vous avez déjà complété ce quiz.", "warning")
            return redirect(url_for('student_events.quiz_result', event_id=event_id, participation_id=existing_participation.id))
        
        # ⚠️ VÉRIFICATION 5 : Déverrouillage séquentiel strict
        completed_count = session.query(EventParticipation).filter(
            and_(
                EventParticipation.event_id == event_id,
                EventParticipation.user_id == current_user.id
            )
        ).count()
        
        expected_quiz = completed_count + 1
        if quiz_number != expected_quiz:
            if quiz_number > expected_quiz:
                flash(f"🔒 Vous devez d'abord compléter le Quiz {expected_quiz}.", "error")
            else:
                flash(f"⚠️ Vous avez déjà complété les {completed_count} premiers quiz.", "warning")
            return redirect(url_for('student_events.event_detail', event_id=event_id))
        
        # Charger les questions
        question_ids = json.loads(quiz.questions)
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        
        # Trier les questions dans l'ordre du JSON
        questions_dict = {q.id: q for q in questions}
        questions_ordered = [questions_dict[qid] for qid in question_ids if qid in questions_dict]
        
        return render_template('student/event_play.html', 
                              event=event, 
                              quiz=quiz, 
                              questions=questions_ordered)
    finally:
        session.close()


@student_events_bp.route('/<event_id>/submit/<int:quiz_number>', methods=['POST'])
@login_required
def submit_quiz(event_id, quiz_number):
    """Soumettre les réponses d'un quiz d'événement"""
    session = SessionLocal()
    try:
        event = session.get(Event, event_id)
        if not event:
            return jsonify({'error': 'Événement introuvable'}), 404
        
        # ⚠️ VÉRIFICATION 1 : Membership
        membership = session.query(GroupMember).filter(
            and_(GroupMember.group_id == event.group_id, GroupMember.user_id == current_user.id)
        ).first()
        
        if not membership:
            return jsonify({'error': 'Accès non autorisé : vous n\'\u00eates pas membre de ce groupe'}), 403
        
        # ⚠️ VÉRIFICATION 2 : Événement actif
        event_status = event.get_status()
        if event_status != 'active':
            return jsonify({'error': 'Événement non actif ou terminé'}), 403
        
        # ⚠️ VÉRIFICATION 3 : Quiz valide
        if quiz_number < 1 or quiz_number > 5:
            return jsonify({'error': 'Numéro de quiz invalide'}), 400
        
        quiz = session.query(EventQuiz).filter(
            and_(EventQuiz.event_id == event_id, EventQuiz.quiz_number == quiz_number)
        ).first()
        
        if not quiz:
            return jsonify({'error': 'Quiz introuvable'}), 404
        
        # ⚠️ VÉRIFICATION 4 : Pas déjà complété
        existing = session.query(EventParticipation).filter(
            and_(
                EventParticipation.quiz_id == quiz.id,
                EventParticipation.user_id == current_user.id
            )
        ).first()
        
        if existing:
            return jsonify({'error': 'Quiz déjà complété'}), 400
        
        # ⚠️ VÉRIFICATION 5 : Déverrouillage séquentiel
        completed_count = session.query(EventParticipation).filter(
            and_(
                EventParticipation.event_id == event_id,
                EventParticipation.user_id == current_user.id
            )
        ).count()
        
        if quiz_number != completed_count + 1:
            return jsonify({'error': f'Vous devez compléter le Quiz {completed_count + 1} d\'abord'}), 403
        
        # Récupérer les réponses
        data = request.get_json()
        answers = data.get('answers', {})
        time_spent = data.get('time_spent', 0)
        
        # Charger les questions et évaluer
        question_ids = json.loads(quiz.questions)
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_dict = {q.id: q for q in questions}
        
        correct_count = 0
        detailed_answers = []
        
        for qid in question_ids:
            if qid not in questions_dict:
                continue
            
            question = questions_dict[qid]
            user_answer = answers.get(qid, "")
            
            # Évaluation simplifiée (QCM uniquement pour l'instant)
            is_correct = False
            if question.type.value == "qcm":
                is_correct = user_answer.strip().lower() == question.answer.strip().lower()
                if is_correct:
                    correct_count += 1
            
            detailed_answers.append({
                'question_id': qid,
                'user_answer': user_answer,
                'correct_answer': question.answer,
                'is_correct': is_correct
            })
        
        # Calculer le score
        score = round((correct_count / len(question_ids)) * 100, 1) if len(question_ids) > 0 else 0
        
        # Enregistrer la participation
        participation = EventParticipation(
            event_id=event_id,
            quiz_id=quiz.id,
            user_id=current_user.id,
            score=score,
            total_questions=len(question_ids),
            time_spent=time_spent,
            answers=json.dumps(detailed_answers)
        )
        session.add(participation)
        session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'correct': correct_count,
            'total': len(question_ids),
            'redirect': url_for('student_events.quiz_result', event_id=event_id, participation_id=participation.id)
        })
    finally:
        session.close()


@student_events_bp.route('/<event_id>/result/<participation_id>')
@login_required
def quiz_result(event_id, participation_id):
    """Afficher le résultat d'un quiz complété"""
    session = SessionLocal()
    try:
        participation = session.get(EventParticipation, participation_id)
        
        if not participation or participation.user_id != current_user.id:
            flash("Résultat introuvable.", "error")
            return redirect(url_for('ui.home'))
        
        event = session.get(Event, event_id)
        quiz = session.get(EventQuiz, participation.quiz_id)
        
        # Charger les détails des réponses
        detailed_answers = json.loads(participation.answers)
        
        # Enrichir avec les questions complètes
        question_ids = [a['question_id'] for a in detailed_answers]
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_dict = {q.id: q for q in questions}
        
        for answer in detailed_answers:
            qid = answer['question_id']
            if qid in questions_dict:
                answer['question'] = questions_dict[qid]
        
        # Progression
        completed_count = session.query(EventParticipation).filter(
            and_(
                EventParticipation.event_id == event_id,
                EventParticipation.user_id == current_user.id
            )
        ).count()
        
        next_quiz = completed_count + 1 if completed_count < 5 else None
        
        return render_template('student/event_result.html',
                              event=event,
                              quiz=quiz,
                              participation=participation,
                              detailed_answers=detailed_answers,
                              next_quiz=next_quiz)
    finally:
        session.close()
