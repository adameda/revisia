<h1 align="center">Révis’IA — Application de Quiz Intelligente (V1)</h1>

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
  <li>📂 Importer ses documents de cours (<code>.docx</code>).</li>
  <li>🧠 Extraire automatiquement le texte pour le transformer en quiz à choix multiples grâce à un <strong>LLM (Google Gemini)</strong>.</li>
  <li>🎮 Répondre question par question avec un feedback immédiat.</li>
  <li>📈 Sauvegarder ses résultats pour suivre sa progression.</li>
</ul>

<hr>

<h2>🏗️ Structure du projet</h2>

<pre>
app-revision-quiz/
│
├── run.py                     → Point d’entrée de l’application Flask
│
├── app/
│   ├── __init__.py            → Création de l’app + enregistrement des Blueprints
│   ├── db.py                  → Configuration SQLite et ORM SQLAlchemy
│   ├── models.py              → Définition des tables (User, Document, Question, Result)
│   ├── extract.py             → Extraction du texte DOCX → Markdown
│   ├── llm.py                 → Génération des quiz via l’API Gemini
│   │
│   ├── routes/                → Logique des pages et API
│   │   ├── ui.py              → Routes HTML principales (home, documents, quiz, etc.)
│   │   ├── documents.py       → Upload, suppression, gestion des fichiers
│   │   ├── quizzes.py         → Génération des quiz
│   │   ├── results.py         → Sauvegarde et consultation des résultats
│   │   └── auth.py            → Connexion / Inscription / Déconnexion
│   │
│   ├── templates/             → Pages HTML (base, home, quiz, login, register, upload, ...)
│   └── static/                → Ressources statiques (CSS, JS, images)
│
└── data.db                    → Base SQLite locale
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

<pre>
User (1) ─── owns ─── (∞) Document ─── has ─── (∞) Question ─── answered_by ─── (∞) Result
</pre>

<ul>
  <li><strong>User</strong> — id, username, email, password_hash, created_at</li>
  <li><strong>Document</strong> — id, title, content, created_at, user_id</li>
  <li><strong>Question</strong> — id, document_id, type, question, choices, answer</li>
  <li><strong>Result</strong> — id, question_id, user_answer, is_correct, reviewed_at</li>
</ul>

<hr>

<h2>💻 Technologies utilisées</h2>

<ul>
  <li>🐍 <strong>Python 3 / Flask</strong> — Framework web principal</li>
  <li><strong>SQLAlchemy</strong> — ORM pour la gestion de la base de données</li>
  <li><strong>TailwindCSS</strong> — Design moderne et responsive</li>
  <li><strong>JavaScript (Fetch API)</strong> — Interaction asynchrone pour les quiz et l’upload</li>
  <li>⚡ <strong>Google Gemini API</strong> — Génération intelligente de quiz</li>
</ul>

<hr>

<h2>🚀 Lancer le projet en local</h2>

<pre><code># 1️⃣ Cloner le projet
git clone https://github.com/adameda/revisia.git
cd revisia

# 2️⃣ Installer les dépendances avec UV
uv sync

# 3️⃣ Activer l’environnement virtuel créé par UV
source .venv/bin/activate   # macOS / Linux
# ou
.\.venv\Scripts\activate     # Windows

# 4️⃣ Lancer l’application Flask
python run.py

# 5️⃣ Accéder à l’app dans le navigateur
http://127.0.0.1:8000
</code></pre>

<hr>

<h2>☁️ V2 — Prochaines étapes</h2>
<ul>
  <li><strong>Déploiement en ligne</strong> sur une plateforme cloud (Railway)</li>
  <li><strong>Phase de test utilisateurs</strong> pour recueillir des retours sur l’expérience et les fonctionnalités</li>
  <li><strong>Amélioration de l’expérience d’apprentissage</strong> (mécanismes de quiz, feedbacks, interface, progression)</li>
</ul>

<hr>

<p>
© 2025 — Créé avec ❤️ par Adam.<br>
</p>
