# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from ..db import SessionLocal
from ..models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

# --- Initialisation Flask-Login ---
login_manager = LoginManager()
login_manager.login_view = "auth.login"


# --- Fonction de chargement utilisateur ---
@login_manager.user_loader
def load_user(user_id):
    session = SessionLocal()
    user = session.get(User, user_id)
    session.close()
    return user


# --- Page d'inscription ---
@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("ui.home"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for("auth.register"))

        session = SessionLocal()
        existing = session.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        if existing:
            flash("Ce compte existe déjà.", "error")
            session.close()
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email)
        user.set_password(password)
        session.add(user)
        session.commit()
        session.close()

        flash("✅ Inscription réussie ! Vous pouvez maintenant vous connecter.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# --- Page de connexion ---
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("ui.home"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        session = SessionLocal()
        user = session.query(User).filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("❌ Identifiants incorrects.", "error")
            session.close()
            return redirect(url_for("auth.login"))

        login_user(user)
        session.close()
        flash(f"👋 Bienvenue, {user.username} !")
        return redirect(url_for("ui.home"))

    return render_template("login.html")


# --- Déconnexion ---
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("👋 Déconnecté avec succès.")
    return redirect(url_for("auth.login"))


# --- Promotion en professeur avec code admin ---
@bp.route("/promote-to-teacher", methods=["POST"])
@login_required
def promote_to_teacher():
    """Promouvoir un utilisateur en professeur avec un code admin"""
    admin_code = request.form.get("admin_code", "").strip()
    
    # Code admin défini dans les variables d'environnement
    correct_code = current_app.config.get("ADMIN_CODE", "PROF2026")
    
    if not admin_code:
        flash("Veuillez entrer un code admin.", "error")
        return redirect(url_for("ui.home"))
    
    if admin_code != correct_code:
        flash("❌ Code admin incorrect.", "error")
        return redirect(url_for("ui.home"))
    
    # Promouvoir l'utilisateur
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(id=current_user.id).first()
        if user:
            if user.is_teacher:
                flash("Vous êtes déjà professeur.", "error")
            else:
                user.is_teacher = True
                session.commit()
                flash(f"🎓 Félicitations {user.username} ! Vous êtes maintenant professeur.", "success")
        session.close()
    except Exception as e:
        session.rollback()
        session.close()
        flash(f"Erreur: {str(e)}", "error")
    
    return redirect(url_for("ui.home"))


# --- Toggle prof/élève (mode debug uniquement) ---
@bp.route("/toggle-teacher", methods=["POST"])
@login_required
def toggle_teacher():
    """Basculer entre prof et élève (pour les tests en mode DEBUG)"""
    if not current_app.config.get("DEBUG", False):
        flash("Cette fonctionnalité n'est disponible qu'en mode debug.", "error")
        return redirect(url_for("ui.home"))
    
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(id=current_user.id).first()
        if user:
            user.is_teacher = not user.is_teacher
            session.commit()
            status = "professeur" if user.is_teacher else "élève"
            flash(f"🔄 Mode basculé : vous êtes maintenant {status}", "success")
        session.close()
    except Exception as e:
        session.rollback()
        session.close()
        flash(f"Erreur: {str(e)}", "error")
    
    return redirect(url_for("ui.home"))
