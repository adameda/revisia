# app/routes/groups.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from ..db import SessionLocal
from ..models import Group, GroupMember, User, Subject, Document, GroupSubject, generate_invite_code

# Blueprint pour les routes professeur
teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

# Blueprint pour les routes élève
groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


# ============================================
# ROUTES PROFESSEUR
# ============================================

@teacher_bp.route("/groups")
@login_required
def list_groups():
    """Liste des groupes créés par le professeur"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette page.", "error")
        return redirect(url_for("ui.home"))
    
    session = SessionLocal()
    try:
        groups = session.query(Group).filter_by(teacher_id=current_user.id).order_by(Group.created_at.desc()).all()
        
        # Compter les membres pour chaque groupe
        groups_with_count = []
        for group in groups:
            member_count = session.query(GroupMember).filter_by(group_id=group.id).count()
            groups_with_count.append({
                'group': group,
                'member_count': member_count
            })
        
        return render_template("teacher/groups.html", groups=groups_with_count)
    finally:
        session.close()


@teacher_bp.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    """Créer un nouveau groupe"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette fonctionnalité.", "error")
        return redirect(url_for("ui.home"))
    
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    
    if not name:
        flash("Le nom du groupe est obligatoire.", "error")
        return redirect(url_for("teacher.list_groups"))
    
    session = SessionLocal()
    try:
        # Générer un code d'invitation unique
        invite_code = generate_invite_code()
        
        # Vérifier l'unicité (très improbable mais sécurité)
        while session.query(Group).filter_by(invite_code=invite_code).first():
            invite_code = generate_invite_code()
        
        # Créer le groupe
        new_group = Group(
            name=name,
            description=description if description else None,
            invite_code=invite_code,
            teacher_id=current_user.id
        )
        
        session.add(new_group)
        session.commit()
        
        flash(f"Groupe '{name}' créé avec succès ! Code: {invite_code}", "success")
        return redirect(url_for("teacher.view_group", group_id=new_group.id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la création du groupe: {str(e)}", "error")
        return redirect(url_for("teacher.list_groups"))
    finally:
        session.close()


@teacher_bp.route("/groups/<group_id>")
@login_required
def view_group(group_id):
    """Voir les détails d'un groupe"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette page.", "error")
        return redirect(url_for("ui.home"))
    
    session = SessionLocal()
    try:
        group = session.query(Group).filter_by(id=group_id, teacher_id=current_user.id).first()
        
        if not group:
            flash("Groupe introuvable.", "error")
            return redirect(url_for("teacher.list_groups"))
        
        # Récupérer les membres avec leurs informations
        members = session.query(GroupMember, User).join(User).filter(GroupMember.group_id == group_id).order_by(GroupMember.joined_at.desc()).all()
        
        members_data = [{'member': member, 'user': user} for member, user in members]
        
        # Récupérer les matières liées au groupe
        group_subjects = session.query(GroupSubject, Subject).join(Subject).filter(GroupSubject.group_id == group_id).order_by(GroupSubject.added_at.desc()).all()
        
        subjects_data = []
        for gs, subject in group_subjects:
            # Compter les cours et quiz de cette matière
            doc_count = session.query(Document).filter_by(subject_id=subject.id).count()
            subjects_data.append({
                'group_subject': gs,
                'subject': subject,
                'document_count': doc_count
            })
        
        # Récupérer les matières du prof non encore liées (pour le dropdown)
        linked_subject_ids = [subject.id for _, subject in group_subjects]
        available_subjects = session.query(Subject).filter(
            Subject.user_id == current_user.id,
            ~Subject.id.in_(linked_subject_ids) if linked_subject_ids else True
        ).order_by(Subject.name).all()
        
        return render_template("teacher/group_detail.html", 
                             group=group, 
                             members=members_data,
                             subjects=subjects_data,
                             available_subjects=available_subjects)
    finally:
        session.close()


@teacher_bp.route("/groups/<group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    """Supprimer un groupe"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette fonctionnalité.", "error")
        return redirect(url_for("ui.home"))
    
    session = SessionLocal()
    try:
        group = session.query(Group).filter_by(id=group_id, teacher_id=current_user.id).first()
        
        if not group:
            flash("Groupe introuvable.", "error")
            return redirect(url_for("teacher.list_groups"))
        
        # ⚠️ PROTECTION : Vérifier les événements liés au groupe
        from ..models import Event
        from datetime import datetime
        
        now = datetime.now()
        
        # Événements actifs (en cours)
        active_events = session.query(Event).filter(
            Event.group_id == group_id,
            Event.start_date <= now,
            Event.end_date >= now
        ).all()
        
        if active_events:
            event_names = ', '.join([e.name for e in active_events])
            flash(f"❌ Impossible de supprimer : {len(active_events)} événement(s) en cours dans ce groupe : {event_names}", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        # Événements futurs (à venir)
        future_events = session.query(Event).filter(
            Event.group_id == group_id,
            Event.start_date > now
        ).all()
        
        if future_events:
            event_names = ', '.join([e.name for e in future_events])
            flash(f"⚠️ Impossible de supprimer : {len(future_events)} événement(s) à venir dans ce groupe : {event_names}. Supprimez d'abord les événements.", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        # Compter les membres
        member_count = session.query(GroupMember).filter_by(group_id=group_id).count()
        
        group_name = group.name
        session.delete(group)
        session.commit()
        
        if member_count > 0:
            flash(f"Groupe '{group_name}' supprimé avec succès ({member_count} membre(s) retiré(s)).", "success")
        else:
            flash(f"Groupe '{group_name}' supprimé avec succès.", "success")
        return redirect(url_for("teacher.list_groups"))
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}", "error")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    finally:
        session.close()


@teacher_bp.route("/groups/<group_id>/subjects/add", methods=["POST"])
@login_required
def add_subject_to_group(group_id):
    """Ajouter une matière au groupe"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette fonctionnalité.", "error")
        return redirect(url_for("ui.home"))
    
    subject_id = request.form.get("subject_id")
    
    if not subject_id:
        flash("Veuillez sélectionner une matière.", "error")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    
    session = SessionLocal()
    try:
        # Vérifier que le groupe appartient au prof
        group = session.query(Group).filter_by(id=group_id, teacher_id=current_user.id).first()
        if not group:
            flash("Groupe introuvable.", "error")
            return redirect(url_for("teacher.list_groups"))
        
        # Vérifier que la matière appartient au prof
        subject = session.query(Subject).filter_by(id=subject_id, user_id=current_user.id).first()
        if not subject:
            flash("Matière introuvable.", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        # Vérifier si déjà liée
        existing = session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first()
        if existing:
            flash("Cette matière est déjà liée au groupe.", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        # Ajouter la liaison
        group_subject = GroupSubject(group_id=group_id, subject_id=subject_id)
        session.add(group_subject)
        session.commit()
        
        flash(f"Matière '{subject.name}' ajoutée au groupe !", "success")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    finally:
        session.close()


@teacher_bp.route("/groups/<group_id>/subjects/<subject_id>/remove", methods=["POST"])
@login_required
def remove_subject_from_group(group_id, subject_id):
    """Retirer une matière du groupe"""
    if not current_user.is_teacher:
        flash("Vous n'avez pas accès à cette fonctionnalité.", "error")
        return redirect(url_for("ui.home"))
    
    session = SessionLocal()
    try:
        # Vérifier que le groupe appartient au prof
        group = session.query(Group).filter_by(id=group_id, teacher_id=current_user.id).first()
        if not group:
            flash("Groupe introuvable.", "error")
            return redirect(url_for("teacher.list_groups"))
        
        # Trouver la liaison
        group_subject = session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first()
        if not group_subject:
            flash("Liaison introuvable.", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        subject = session.query(Subject).filter_by(id=subject_id).first()
        subject_name = subject.name if subject else "la matière"
        
        # ⚠️ NOUVEAU : Vérifier si la matière est utilisée dans des événements du groupe
        from ..models import Event
        from datetime import datetime
        
        now = datetime.now()
        
        # Événements actifs
        active_events = session.query(Event).filter(
            Event.group_id == group_id,
            Event.subject_id == subject_id,
            Event.start_date <= now,
            Event.end_date >= now
        ).all()
        
        if active_events:
            event_names = ', '.join([e.name for e in active_events])
            flash(f"❌ Impossible : cette matière est utilisée dans {len(active_events)} événement(s) en cours : {event_names}", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        # Événements futurs
        future_events = session.query(Event).filter(
            Event.group_id == group_id,
            Event.subject_id == subject_id,
            Event.start_date > now
        ).all()
        
        if future_events:
            event_names = ', '.join([e.name for e in future_events])
            flash(f"⚠️ Impossible : cette matière est utilisée dans {len(future_events)} événement(s) à venir : {event_names}. Supprimez d'abord les événements.", "error")
            return redirect(url_for("teacher.view_group", group_id=group_id))
        
        session.delete(group_subject)
        session.commit()
        
        flash(f"Matière '{subject_name}' retirée du groupe.", "success")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for("teacher.view_group", group_id=group_id))
    finally:
        session.close()


# ============================================
# ROUTES ÉLÈVE
# ============================================

@groups_bp.route("/")
@login_required
def list_groups():
    """Liste des groupes auxquels l'élève appartient"""
    session = SessionLocal()
    try:
        # Récupérer les groupes via les memberships (avec jointures explicites)
        memberships = (
            session.query(GroupMember, Group, User)
            .join(Group, GroupMember.group_id == Group.id)
            .join(User, Group.teacher_id == User.id)
            .filter(GroupMember.user_id == current_user.id)
            .order_by(GroupMember.joined_at.desc())
            .all()
        )
        
        groups_data = []
        for membership, group, teacher in memberships:
            member_count = session.query(GroupMember).filter_by(group_id=group.id).count()
            subjects_count = session.query(GroupSubject).filter_by(group_id=group.id).count()
            
            # Créer un objet avec les attributs attendus par le template
            group_info = type('obj', (object,), {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'teacher': teacher,
                'members_count': member_count,
                'subjects_count': subjects_count
            })()
            
            groups_data.append(group_info)
        
        return render_template("groups/index.html", groups=groups_data)
    finally:
        session.close()


@groups_bp.route("/join", methods=["POST"])
@login_required
def join_group():
    """Rejoindre un groupe avec un code d'invitation"""
    invite_code = request.form.get("invite_code", "").strip().upper()
    
    if not invite_code:
        flash("Veuillez entrer un code d'invitation.", "error")
        return redirect(url_for("groups.list_groups"))
    
    session = SessionLocal()
    try:
        # Rechercher le groupe
        group = session.query(Group).filter(func.upper(Group.invite_code) == invite_code).first()
        
        if not group:
            flash("Code d'invitation invalide.", "error")
            return redirect(url_for("groups.list_groups"))
        
        # Vérifier si l'utilisateur est déjà membre
        existing_member = session.query(GroupMember).filter_by(
            group_id=group.id,
            user_id=current_user.id
        ).first()
        
        if existing_member:
            flash("Vous êtes déjà membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))
        
        # Ajouter le membre
        new_member = GroupMember(
            group_id=group.id,
            user_id=current_user.id
        )
        
        session.add(new_member)
        session.commit()
        
        flash(f"Vous avez rejoint le groupe '{group.name}' !", "success")
        return redirect(url_for("groups.view_group", group_id=group.id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de l'adhésion au groupe: {str(e)}", "error")
        return redirect(url_for("groups.list_groups"))
    finally:
        session.close()


@groups_bp.route("/<group_id>")
@login_required
def view_group(group_id):
    """Voir les détails d'un groupe (vue élève)"""
    session = SessionLocal()
    try:
        # Vérifier que l'utilisateur est membre
        membership = session.query(GroupMember).filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))
        
        # Récupérer les infos du groupe
        group = session.query(Group).filter_by(id=group_id).first()
        teacher = session.query(User).filter_by(id=group.teacher_id).first()
        member_count = session.query(GroupMember).filter_by(group_id=group_id).count()
        
        # Récupérer les matières liées au groupe
        group_subjects = session.query(GroupSubject, Subject).join(Subject).filter(GroupSubject.group_id == group_id).order_by(Subject.name).all()
        
        subjects_data = []
        for gs, subject in group_subjects:
            # Compter les cours de cette matière
            doc_count = session.query(Document).filter_by(subject_id=subject.id).count()
            subjects_data.append({
                'subject': subject,
                'document_count': doc_count
            })
        
        return render_template("groups/detail.html", 
                             group=group, 
                             teacher=teacher,
                             member_count=member_count,
                             subjects=subjects_data)
    finally:
        session.close()


@groups_bp.route("/<group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id):
    """Quitter un groupe"""
    session = SessionLocal()
    try:
        # Trouver le membership
        membership = session.query(GroupMember).filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))
        
        group = session.query(Group).filter_by(id=group_id).first()
        group_name = group.name if group else "le groupe"
        
        # ⚠️ PROTECTION : Vérifier les participations à des événements actifs
        from ..models import Event, EventParticipation
        from datetime import datetime
        
        now = datetime.now()
        
        # Événements actifs auxquels l'élève participe
        active_participations = session.query(EventParticipation).join(
            Event, EventParticipation.event_id == Event.id
        ).filter(
            Event.group_id == group_id,
            EventParticipation.user_id == current_user.id,
            Event.start_date <= now,
            Event.end_date >= now
        ).all()
        
        if active_participations:
            event_ids = list(set([p.event_id for p in active_participations]))
            events = session.query(Event).filter(Event.id.in_(event_ids)).all()
            event_names = ', '.join([e.name for e in events])
            flash(f"❌ Impossible de quitter : vous participez actuellement à {len(events)} événement(s) en cours : {event_names}. Attendez la fin des événements.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))
        
        # Vérifier les événements futurs
        future_participations = session.query(EventParticipation).join(
            Event, EventParticipation.event_id == Event.id
        ).filter(
            Event.group_id == group_id,
            EventParticipation.user_id == current_user.id,
            Event.start_date > now
        ).all()
        
        if future_participations:
            event_ids = list(set([p.event_id for p in future_participations]))
            events = session.query(Event).filter(Event.id.in_(event_ids)).all()
            event_names = ', '.join([e.name for e in events])
            # Avertissement mais on autorise quand même
            flash(f"⚠️ Vous êtes inscrit à {len(events)} événement(s) à venir : {event_names}. Vos participations seront perdues.", "warning")
        
        session.delete(membership)
        session.commit()
        
        flash(f"Vous avez quitté {group_name}.", "success")
        return redirect(url_for("groups.list_groups"))
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la sortie du groupe: {str(e)}", "error")
        return redirect(url_for("groups.view_group", group_id=group_id))
    finally:
        session.close()


@groups_bp.route("/<group_id>/subjects/<subject_id>/documents")
@login_required
def view_subject_documents(group_id, subject_id):
    """Voir les cours d'une matière du groupe (élève)"""
    session = SessionLocal()
    try:
        # Vérifier que l'utilisateur est membre
        membership = session.query(GroupMember).filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))
        
        # Vérifier que la matière est liée au groupe
        group_subject = session.query(GroupSubject).filter_by(
            group_id=group_id,
            subject_id=subject_id
        ).first()
        
        if not group_subject:
            flash("Cette matière n'est pas disponible dans ce groupe.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))
        
        # Récupérer la matière et ses cours
        subject = session.query(Subject).filter_by(id=subject_id).first()
        documents = session.query(Document).filter_by(subject_id=subject_id).order_by(Document.created_at.desc()).all()
        
        # Récupérer les infos du groupe
        group = session.query(Group).filter_by(id=group_id).first()
        
        return render_template("groups/subject_documents.html",
                             group=group,
                             subject=subject,
                             documents=documents)
    finally:
        session.close()


@groups_bp.route("/<group_id>/subjects/<subject_id>/documents/<document_id>")
@login_required
def view_document(group_id, subject_id, document_id):
    """Lire un cours spécifique (lecture seule, vue élève)"""
    session = SessionLocal()
    try:
        # Vérifier que l'utilisateur est membre
        membership = session.query(GroupMember).filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()
        
        if not membership:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))
        
        # Vérifier que la matière est liée au groupe
        group_subject = session.query(GroupSubject).filter_by(
            group_id=group_id,
            subject_id=subject_id
        ).first()
        
        if not group_subject:
            flash("Cette matière n'est pas disponible dans ce groupe.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))
        
        # Récupérer le document
        document = session.query(Document).filter_by(
            id=document_id,
            subject_id=subject_id
        ).first()
        
        if not document:
            flash("Document introuvable.", "error")
            return redirect(url_for("groups.view_subject_documents", group_id=group_id, subject_id=subject_id))
        
        # Retourner le contenu en JSON (pour modal)
        return jsonify({
            'title': document.title,
            'content': document.content
        })
    finally:
        session.close()
