<h1 align="center">Révis’IA — Application de Quiz Intelligente (V2)</h1>

<p align="center">
  <img src="app/static/img/logo.svg" alt="Logo Révis’IA" width="100" style="border-radius: 12px;">
</p>

<p align="center">
  <strong>Révis’IA</strong> est une application Flask qui transforme automatiquement tes cours en quiz à l’aide d’un modèle d’intelligence artificielle.<br>
  Simple et intuitive, l’application te permettra de revoir tes cours efficacement.
</p>

<hr>

<h2>⌯⌲ Objectif</h2>
<p>
L’application permet à un utilisateur de :
</p>
<ul>
  <li>Importer ses documents de cours (<code>.docx</code>).</li>
  <li>Extraire automatiquement le texte pour le transformer en quiz à choix multiples grâce à un <strong>LLM (Google Gemini)</strong>.</li>
  <li>Répondre question par question avec un feedback immédiat.</li>
  <li>Sauvegarder ses résultats pour suivre sa progression.</li>
  <li>Affronter ses amis sur ses cours grâce au nouveau système de <strong>GROUP/EVENTS</strong>.</li>
</ul>

<hr>

<h2>🏗️ Structure du projet</h2>

<pre>
revisia/
│
├── run.py                     → Point d’entrée de l’application Flask (factory)
├── Dockerfile                 → Image Docker pour l’application
├── docker-compose.yml         → Compose pour Postgres + app (local)
├── pyproject.toml             → Dépendances et configuration (UV)
├── railway.json               → Configuration de déploiement (Railway)
│
├── app/                       → Code applicatif
│   ├── __init__.py            → Création de l'app, blueprints, config
│   ├── db.py                  → Connexion SQLAlchemy (PostgreSQL)
│   ├── extensions.py          → Extensions Flask (login, migrate, etc.)
│   ├── models.py              → Modèles SQLAlchemy (users, documents, questions, events, ...)
│   ├── extract.py             → Extraction DOCX → Markdown
│   ├── llm.py                 → Wrapper pour l’API Gemini / fallback
│   │
│   ├── routes/                → Blueprints et routes (auth, documents, quizzes, events, ...)
│   ├── templates/             → Templates Jinja2
│   └── static/                → CSS / JS / images
│
├── outputs/                   → Fichiers JSON générés lors des tests/demos
├── tests/                     → Tests unitaires et d’intégration (pytest)
└── README.md
</pre>

<hr>

<h2>⚙️ Fonctionnement</h2>

<ol>
  <li><strong>Upload d’un document</strong> : l’utilisateur charge un fichier .docx via l’interface.</li>
  <li><strong>Extraction</strong> : le texte est converti en Markdown lisible par l’IA.</li>
  <li><strong>Génération du quiz</strong> : un prompt structuré est envoyé au modèle Gemini qui renvoie un JSON de questions.</li>
  <li><strong>Stockage</strong> : les questions sont enregistrées dans la base SQLite.</li>
  <li><strong>Jouer</strong> : l’utilisateur répond question par question et reçoit un feedback immédiat.</li>
  <li><strong>Résultats</strong> : le score est sauvegardé et visible dans l’historique.</li>
</ol>

<hr>

<h2>⛁ Base de données</h2>

<p>La V2 utilise PostgreSQL via SQLAlchemy. La connexion est lue depuis la variable d'environnement <code>DATABASE_URL</code>. Les tables principales sont :</p>

<ul>
  <li><strong>User</strong> — id (UUID string), username, email, password_hash, created_at</li>
  <li><strong>Subject</strong> — matières, liées à un utilisateur</li>
  <li><strong>Document</strong> — id, title, content, subject_id, user_id, created_at</li>
  <li><strong>Question</strong> — id, document_id, type (ENUM), question, choices (JSON), answer, explanation</li>
  <li><strong>Result</strong> — id, question_id, user_id, user_answer, is_correct, evaluation, reviewed_at</li>
  <li><strong>QuizSession</strong> — session de jeu, score, total_questions, played_at</li>
  <li><strong>QuizGeneration</strong> — compteur de génération (par user/jour)</li>
  <li><strong>Group / GroupMember / GroupSubject</strong> — gestion des groupes et permissions</li>
  <li><strong>Event / EventQuiz / EventParticipation</strong> — compétitions et participations</li>
</ul>

<p>Remarques :</p>
<ul>
  <li>L'initialisation de la BDD (création des tables) se fait via <code>init_db()</code> dans <code>app/db.py</code>.</li>
  <li>En local via Docker Compose, les variables <code>POSTGRES_DB</code>, <code>POSTGRES_USER</code> et <code>POSTGRES_PASSWORD</code> sont utilisées pour construire <code>DATABASE_URL</code>.</li>
</ul>

<hr>

<h2>💻 Technologies utilisées</h2>

<ul>
  <li><strong>Python 3 / Flask</strong> — Framework web principal</li>
  <li><strong>SQLAlchemy</strong> — ORM pour la gestion de la base de données</li>
  <li><strong>TailwindCSS</strong> — Design moderne et responsive</li>
  <li><strong>JavaScript (Fetch API)</strong> — Interaction asynchrone pour les quiz et l’upload</li>
  <li><strong>Google Gemini API</strong> — Génération intelligente de quiz</li>
</ul>

<hr>

<h2>🚀 Lancer le projet en local</h2>

<pre><code># 1️⃣ Cloner le projet
git clone https://github.com/adameda/revisia.git
cd revisia

# 2️⃣ Installer les dépendances avec UV
`uv sync`

# 3️⃣ Activer l’environnement virtuel créé par UV
`source .venv/bin/activate`   # macOS / Linux

# 4️⃣ Lancer l’application Flask (dev)
`python run.py`

# 5️⃣ Accéder à l'app dans le navigateur
`http://127.0.0.1:8000`

ou en Docker Compose (Postgres + app) :

`docker compose up --build`
</code></pre>

<hr>

<h2>📁 Fichier .env (exemple)</h2>

<p>Crée un fichier `.env` à la racine (ne pas le committer). Exemple :</p>

<pre>
POSTGRES_DB=revisia_db
POSTGRES_USER=revisia_user
POSTGRES_PASSWORD=change_me
DATABASE_URL=postgresql://revisia_user:change_me@localhost:5432/revisia_db
SECRET_KEY=une_chaine_secrete_longue
GEMINI_API_KEY=clé_gemini_principale
GEMINI_API_KEY_2=clé_gemini_secondaire
MOCK_GEMINI=False
REGISTRATION_ENABLED=True
QUIZ_LIMIT_ENABLED=False
DAILY_QUIZ_LIMIT=50
PORT=8000
</pre>

<hr>

<h2>🐳 Docker</h2>

<p>Le projet fournit un <code>Dockerfile</code> optimisé et un <code>docker-compose.yml</code> pour démarrer une base PostgreSQL et l’application :</p>

<ul>
  <li>Construire et lancer : <code>docker compose up --build</code></li>
  <li>Le service <code>web</code> expose le port <code>8000</code> et se connecte au service <code>db</code>.</li>
  <li>Les variables d’environnement sont passées via un fichier `.env` ou votre système d’orchestration.</li>
</ul>

<hr>

<h2>🚢 Déploiement</h2>

<p>Le projet est prêt pour un déploiement Docker (Railway, Render, Fly, etc.). Quelques conseils :</p>

<ul>
  <li>Sur Railway : utiliser le `Dockerfile` et définir les variables d’environnement (notamment <code>DATABASE_URL</code>, <code>SECRET_KEY</code>, et les clés Gemini).</li>
  <li>Si vous ajoutez une base Postgres via la plateforme, utilisez l’URL fournie comme <code>DATABASE_URL</code>.</li>
  <li>Configurer le nombre de workers Gunicorn via la variable d’environnement ou dans le service si besoin.</li>
  <li>Pensez à activer les backups de la base et à sécuriser les clés API.</li>
</ul>

<hr>

<p>
© 2025 — Créé avec ❤️ par Adam.<br>
</p>
