# app/routes/auth.py
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