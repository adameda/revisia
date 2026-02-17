# app/routes/groups.py
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from ..db import SessionLocal
from ..models import Group, GroupMember, User, Subject, Document, GroupSubject, generate_invite_code

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")
logger = logging.getLogger("app.groups")


# ============================================
# HELPERS
# ============================================

def _get_group_access(session, group_id, user_id):
    """Retourne (group, is_owner, is_member). None si groupe introuvable."""
    group = session.get(Group, group_id)
    if not group:
        return None, False, False
    is_owner = group.owner_id == user_id
    is_member = is_owner or session.query(GroupMember).filter_by(
        group_id=group_id, user_id=user_id
    ).first() is not None
    return group, is_owner, is_member


# ============================================
# ROUTES
# ============================================

@groups_bp.route("/")
@login_required
def list_groups():
    """Liste unifiée : groupes créés et groupes rejoints."""
    session = SessionLocal()
    try:
        # Groupes dont l'utilisateur est propriétaire
        owned = session.query(Group).filter_by(owner_id=current_user.id).order_by(Group.created_at.desc()).all()

        # Groupes dont l'utilisateur est membre (mais pas propriétaire)
        joined_rows = (
            session.query(GroupMember, Group, User)
            .join(Group, GroupMember.group_id == Group.id)
            .join(User, Group.owner_id == User.id)
            .filter(GroupMember.user_id == current_user.id, Group.owner_id != current_user.id)
            .order_by(GroupMember.joined_at.desc())
            .all()
        )

        groups_data = []

        for group in owned:
            member_count = session.query(GroupMember).filter_by(group_id=group.id).count()
            groups_data.append({
                'group': group,
                'is_owner': True,
                'member_count': member_count,
                'owner': None,
            })

        for _membership, group, owner in joined_rows:
            member_count = session.query(GroupMember).filter_by(group_id=group.id).count()
            groups_data.append({
                'group': group,
                'is_owner': False,
                'member_count': member_count,
                'owner': owner,
            })

        return render_template("groups/index.html", groups=groups_data)
    finally:
        session.close()


@groups_bp.route("/create", methods=["POST"])
@login_required
def create_group():
    """Créer un nouveau groupe. L'utilisateur en devient le propriétaire et premier membre."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Le nom du groupe est obligatoire.", "error")
        return redirect(url_for("groups.list_groups"))

    session = SessionLocal()
    try:
        invite_code = generate_invite_code()
        while session.query(Group).filter_by(invite_code=invite_code).first():
            invite_code = generate_invite_code()

        new_group = Group(
            name=name,
            description=description or None,
            invite_code=invite_code,
            owner_id=current_user.id,
        )
        session.add(new_group)
        session.flush()

        # Ajouter le propriétaire comme premier membre
        session.add(GroupMember(group_id=new_group.id, user_id=current_user.id))
        session.commit()

        logger.info(f"Groupe créé : '{name}' (code: {invite_code}) par {current_user.username}")
        flash(f"Groupe '{name}' créé ! Code : {invite_code}", "success")
        return redirect(url_for("groups.view_group", group_id=new_group.id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur lors de la création : {e}", "error")
        return redirect(url_for("groups.list_groups"))
    finally:
        session.close()


@groups_bp.route("/join", methods=["POST"])
@login_required
def join_group():
    """Rejoindre un groupe avec un code d'invitation."""
    invite_code = request.form.get("invite_code", "").strip().upper()

    if not invite_code:
        flash("Veuillez entrer un code d'invitation.", "error")
        return redirect(url_for("groups.list_groups"))

    session = SessionLocal()
    try:
        group = session.query(Group).filter(func.upper(Group.invite_code) == invite_code).first()
        if not group:
            flash("Code d'invitation invalide.", "error")
            return redirect(url_for("groups.list_groups"))

        existing = session.query(GroupMember).filter_by(group_id=group.id, user_id=current_user.id).first()
        if existing:
            flash("Vous êtes déjà membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))

        session.add(GroupMember(group_id=group.id, user_id=current_user.id))
        session.commit()

        logger.info(f"{current_user.username} a rejoint le groupe '{group.name}'")
        flash(f"Vous avez rejoint le groupe '{group.name}' !", "success")
        return redirect(url_for("groups.view_group", group_id=group.id))
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("groups.list_groups"))
    finally:
        session.close()


@groups_bp.route("/<group_id>")
@login_required
def view_group(group_id):
    """Vue unifiée du groupe : propriétaire voit les contrôles de gestion, membres voient les matières."""
    session = SessionLocal()
    try:
        group, is_owner, is_member = _get_group_access(session, group_id, current_user.id)
        if not group:
            flash("Groupe introuvable.", "error")
            return redirect(url_for("groups.list_groups"))
        if not is_member:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))

        # Membres
        members_rows = (
            session.query(GroupMember, User)
            .join(User)
            .filter(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at.desc())
            .all()
        )
        members_data = [{'member': m, 'user': u, 'is_owner': u.id == group.owner_id} for m, u in members_rows]

        # Propriétaire
        owner = session.get(User, group.owner_id)

        # Matières liées
        group_subjects = (
            session.query(GroupSubject, Subject)
            .join(Subject)
            .filter(GroupSubject.group_id == group_id)
            .order_by(Subject.name)
            .all()
        )
        subjects_data = []
        for gs, subject in group_subjects:
            doc_count = session.query(Document).filter_by(subject_id=subject.id).count()
            subjects_data.append({'group_subject': gs, 'subject': subject, 'document_count': doc_count})

        # Matières disponibles à ajouter (celles du propriétaire non encore liées)
        available_subjects = []
        if is_owner:
            linked_ids = [s.id for _, s in group_subjects]
            q = session.query(Subject).filter(Subject.user_id == current_user.id)
            if linked_ids:
                q = q.filter(~Subject.id.in_(linked_ids))
            available_subjects = q.order_by(Subject.name).all()

        return render_template(
            "groups/detail.html",
            group=group,
            owner=owner,
            is_owner=is_owner,
            members=members_data,
            subjects=subjects_data,
            available_subjects=available_subjects,
            member_count=len(members_data),
        )
    finally:
        session.close()


@groups_bp.route("/<group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    """Supprimer un groupe (propriétaire uniquement)."""
    session = SessionLocal()
    try:
        group, is_owner, _ = _get_group_access(session, group_id, current_user.id)
        if not group or not is_owner:
            flash("Groupe introuvable ou accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        from ..models import Event
        from datetime import datetime
        now = datetime.now()

        active = session.query(Event).filter(Event.group_id == group_id, Event.start_date <= now, Event.end_date >= now).all()
        if active:
            names = ', '.join(e.name for e in active)
            flash(f"❌ Impossible : {len(active)} événement(s) en cours : {names}", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        future = session.query(Event).filter(Event.group_id == group_id, Event.start_date > now).all()
        if future:
            names = ', '.join(e.name for e in future)
            flash(f"⚠️ Impossible : {len(future)} événement(s) à venir : {names}. Supprimez-les d'abord.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        group_name = group.name
        session.delete(group)
        session.commit()
        logger.info(f"Groupe supprimé : '{group_name}' par {current_user.username}")
        flash(f"Groupe '{group_name}' supprimé.", "success")
        return redirect(url_for("groups.list_groups"))
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("groups.view_group", group_id=group_id))
    finally:
        session.close()


@groups_bp.route("/<group_id>/subjects/add", methods=["POST"])
@login_required
def add_subject_to_group(group_id):
    """Ajouter une matière au groupe (propriétaire uniquement)."""
    subject_id = request.form.get("subject_id")
    if not subject_id:
        flash("Veuillez sélectionner une matière.", "error")
        return redirect(url_for("groups.view_group", group_id=group_id))

    session = SessionLocal()
    try:
        group, is_owner, _ = _get_group_access(session, group_id, current_user.id)
        if not group or not is_owner:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        subject = session.query(Subject).filter_by(id=subject_id, user_id=current_user.id).first()
        if not subject:
            flash("Matière introuvable.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        if session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first():
            flash("Cette matière est déjà liée au groupe.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        session.add(GroupSubject(group_id=group_id, subject_id=subject_id))
        session.commit()
        logger.info(f"Matière '{subject.name}' ajoutée au groupe '{group.name}' par {current_user.username}")
        flash(f"Matière '{subject.name}' ajoutée !", "success")
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
    finally:
        session.close()
    return redirect(url_for("groups.view_group", group_id=group_id))


@groups_bp.route("/<group_id>/subjects/<subject_id>/remove", methods=["POST"])
@login_required
def remove_subject_from_group(group_id, subject_id):
    """Retirer une matière du groupe (propriétaire uniquement)."""
    session = SessionLocal()
    try:
        group, is_owner, _ = _get_group_access(session, group_id, current_user.id)
        if not group or not is_owner:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        gs = session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first()
        if not gs:
            flash("Liaison introuvable.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        subject = session.query(Subject).filter_by(id=subject_id).first()
        subject_name = subject.name if subject else "la matière"

        from ..models import Event
        from datetime import datetime
        now = datetime.now()

        active = session.query(Event).filter(Event.group_id == group_id, Event.subject_id == subject_id, Event.start_date <= now, Event.end_date >= now).all()
        if active:
            flash(f"❌ Impossible : matière utilisée dans {len(active)} événement(s) en cours.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        future = session.query(Event).filter(Event.group_id == group_id, Event.subject_id == subject_id, Event.start_date > now).all()
        if future:
            flash(f"⚠️ Impossible : matière utilisée dans {len(future)} événement(s) à venir.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        session.delete(gs)
        session.commit()
        logger.info(f"Matière '{subject_name}' retirée du groupe par {current_user.username}")
        flash(f"Matière '{subject_name}' retirée.", "success")
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
    finally:
        session.close()
    return redirect(url_for("groups.view_group", group_id=group_id))


@groups_bp.route("/<group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id):
    """Quitter un groupe (les propriétaires ne peuvent pas quitter, ils doivent supprimer)."""
    session = SessionLocal()
    try:
        group, is_owner, is_member = _get_group_access(session, group_id, current_user.id)

        if not group or not is_member:
            flash("Vous n'êtes pas membre de ce groupe.", "error")
            return redirect(url_for("groups.list_groups"))

        if is_owner:
            flash("En tant que propriétaire, vous ne pouvez pas quitter le groupe. Supprimez-le à la place.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        from ..models import Event, EventParticipation
        from datetime import datetime
        now = datetime.now()

        active_participations = (
            session.query(EventParticipation)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(Event.group_id == group_id, EventParticipation.user_id == current_user.id,
                    Event.start_date <= now, Event.end_date >= now)
            .all()
        )
        if active_participations:
            flash("❌ Impossible : vous participez à un événement en cours.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        membership = session.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
        group_name = group.name
        session.delete(membership)
        session.commit()
        logger.info(f"{current_user.username} a quitté le groupe '{group_name}'")
        flash(f"Vous avez quitté '{group_name}'.", "success")
        return redirect(url_for("groups.list_groups"))
    except Exception as e:
        session.rollback()
        flash(f"Erreur : {e}", "error")
        return redirect(url_for("groups.view_group", group_id=group_id))
    finally:
        session.close()


@groups_bp.route("/<group_id>/subjects/<subject_id>/documents")
@login_required
def view_subject_documents(group_id, subject_id):
    """Voir les cours d'une matière du groupe."""
    session = SessionLocal()
    try:
        group, _, is_member = _get_group_access(session, group_id, current_user.id)
        if not group or not is_member:
            flash("Accès non autorisé.", "error")
            return redirect(url_for("groups.list_groups"))

        gs = session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first()
        if not gs:
            flash("Matière non disponible dans ce groupe.", "error")
            return redirect(url_for("groups.view_group", group_id=group_id))

        subject = session.get(Subject, subject_id)
        documents = session.query(Document).filter_by(subject_id=subject_id).order_by(Document.created_at.desc()).all()

        return render_template("groups/subject_documents.html", group=group, subject=subject, documents=documents)
    finally:
        session.close()


@groups_bp.route("/<group_id>/subjects/<subject_id>/documents/<document_id>")
@login_required
def view_document(group_id, subject_id, document_id):
    """Contenu d'un cours (JSON pour modal)."""
    session = SessionLocal()
    try:
        _, _, is_member = _get_group_access(session, group_id, current_user.id)
        if not is_member:
            return jsonify({'error': 'Accès non autorisé'}), 403

        gs = session.query(GroupSubject).filter_by(group_id=group_id, subject_id=subject_id).first()
        if not gs:
            return jsonify({'error': 'Matière non disponible'}), 404

        doc = session.query(Document).filter_by(id=document_id, subject_id=subject_id).first()
        if not doc:
            return jsonify({'error': 'Document introuvable'}), 404

        return jsonify({'title': doc.title, 'content': doc.content})
    finally:
        session.close()
