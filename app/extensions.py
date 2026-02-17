# app/extensions.py
# Extensions Flask partagées (évite les imports circulaires).
# On crée les instances ici, on les initialise dans __init__.py avec init_app().

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# --- Protection CSRF ---
# Génère un token secret unique par session.
# Chaque formulaire et requête AJAX doit l'envoyer pour prouver
# que la requête vient bien de notre site (pas d'un site malveillant).
csrf = CSRFProtect()

# --- Rate Limiter ---
# Limite le nombre de requêtes par IP pour éviter le spam et le brute-force.
# Format : "X per minute" ou "X per hour"
limiter = Limiter(
    key_func=get_remote_address,       # On identifie chaque visiteur par son IP
    default_limits=["120 per minute"],  # Règle globale par défaut
    storage_uri="memory://",           # Stockage en mémoire (suffisant pour un petit projet)
)
