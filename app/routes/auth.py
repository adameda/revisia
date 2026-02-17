# app/routes/auth.py
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
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
logger = logging.getLogger("app.auth")

# Import du rate limiter (défini dans extensions.py)
# On l'applique sur login/register pour bloquer les attaques par brute-force
from ..extensions import limiter

# --- Initialisation Flask-Login ---
login_manager = LoginManager()
login_manager.login_view = "auth.login"


# --- Fonction de chargement utilisateur ---
@login_manager.user_loader
def load_user(user_id):
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        return user
    finally:
        session.close()


# --- Page d'inscription ---
# Limite : 5 inscriptions par minute par IP (anti-spam)
@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    from flask import current_app
    if current_user.is_authenticated:
        return redirect(url_for("ui.home"))

    if not current_app.config.get("REGISTRATION_ENABLED", True):
        return render_template("register.html", registration_enabled=False)

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for("auth.register"))

        session = SessionLocal()
        try:
            existing = session.query(User).filter(
                (User.email == email) | (User.username == username)
            ).first()
            if existing:
                flash("Ce compte existe déjà.", "error")
                return redirect(url_for("auth.register"))

            user = User(username=username, email=email)
            user.set_password(password)
            session.add(user)
            session.commit()

            logger.info(f"Inscription : {username} ({email})")
            flash("✅ Inscription réussie ! Vous pouvez maintenant vous connecter.")
            return redirect(url_for("auth.login"))
        except Exception as e:
            session.rollback()
            flash(f"Erreur : {e}", "error")
            return redirect(url_for("auth.register"))
        finally:
            session.close()

    return render_template("register.html", registration_enabled=True)


# --- Page de connexion ---
# Limite : 5 tentatives par minute par IP (anti brute-force)
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("ui.home"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        session = SessionLocal()
        try:
            user = session.query(User).filter_by(email=email).first()

            if not user or not user.check_password(password):
                logger.warning(f"Échec connexion : {email}")
                flash("❌ Identifiants incorrects.", "error")
                return redirect(url_for("auth.login"))

            login_user(user)
            logger.info(f"Connexion : {user.username} ({email})")
            flash(f"👋 Bienvenue, {user.username} !")
            return redirect(url_for("ui.home"))
        finally:
            session.close()

    return render_template("login.html")


# --- Déconnexion ---
@bp.route("/logout")
@login_required
def logout():
    logger.info(f"Déconnexion : {current_user.username}")
    logout_user()
    flash("👋 Déconnecté avec succès.")
    return redirect(url_for("auth.login"))
