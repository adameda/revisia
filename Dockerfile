# Dockerfile pour Révis'IA (Flask + uv + PostgreSQL)
# Utilise Python slim + uv pour la gestion des packages

FROM python:3.14-slim

# Copier uv depuis l'image officielle
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Installer les dépendances système nécessaires pour pycairo et autres
RUN apt-get update && apt-get install -y \
	gcc \
	g++ \
	pkg-config \
	libcairo2-dev \
	&& rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml uv.lock ./

# Installer les dépendances avec uv (sans installer le projet)
RUN uv sync --frozen --no-install-project --no-dev

# Copier tout le code de l'application
COPY . .

# Installer le projet
RUN uv sync --frozen --no-dev

# Définir le PATH pour utiliser le venv
ENV PATH="/app/.venv/bin:$PATH"

# Déclarer PORT comme argument de build pour Railway
ARG PORT
ENV PORT=${PORT:-8000}

# Variables d'environnement Flask
ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

# Exposer le port
EXPOSE $PORT

# Commande de démarrage (exec pour gestion propre des signaux)
CMD exec gunicorn run:app --bind 0.0.0.0:$PORT --workers 2
