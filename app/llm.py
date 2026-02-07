# app/llm.py

import os
import json
import random
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types 

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"

# Mode mock pour le développement
MOCK_MODE = os.getenv("MOCK_GEMINI", "False").lower() == "true"


# --- Modèle de sortie attendu ---
class QuizItem(BaseModel):
    type: str = Field(description="Type de question, ici toujours 'qcm'.")
    question: str = Field(description="Intitulé de la question.")
    choices: List[str] = Field(description="Liste des 4 choix possibles.")
    answer: str = Field(description="Réponse correcte.")

class QuizResponse(BaseModel):
    items: List[QuizItem]


# --- Template du prompt ---
PROMPT_TEMPLATE = """
**INSTRUCTIONS :**

Tu es un générateur de quiz pédagogique expert. Ta mission est de créer un ensemble de questions à choix multiples (QCM) basées **uniquement** sur le cours fourni ci-dessous.

**Règle absolue :**
- N’utilise **aucune connaissance externe**.
- Chaque question et sa réponse correcte doivent être **directement justifiables** par le cours donné.

**TÂCHES :**
1. Génère **{nb_questions} questions QCM** pour enrichir une base de données.
2. Le jeu de questions doit **couvrir TOUT le cours** de manière équilibrée : définitions, concepts, noms, dates.
3. Chaque question doit :
   - être courte et claire ;
   - avoir **4 choix plausibles** ;
   - contenir **une seule réponse correcte** ;
   - éviter les formulations ambiguës ou évidentes.
4. Les réponses doivent être précises.

COURS À ANALYSER :
<<<
{texte}
<<<
"""


def generate_mock_quiz(text: str, total_questions: int = 20) -> List[dict]:
    """
    Génère un quiz mocké pour le développement.
    Évite les appels API coûteux pendant les tests.
    """
    print(f"🧪 MODE MOCK ACTIVÉ - Génération de {total_questions} questions fictives")
    
    # Extraire quelques mots clés du texte pour rendre les questions plus réalistes
    words = text.split()[:50]  # Premiers 50 mots
    sample_words = random.sample([w for w in words if len(w) > 4], min(10, len([w for w in words if len(w) > 4])))
    
    questions = []
    question_types = [
        "Quelle est la définition de {word} ?",
        "Parmi ces propositions, laquelle concerne {word} ?",
        "Quel concept est lié à {word} ?",
        "Comment peut-on décrire {word} ?",
        "Quelle affirmation est vraie concernant {word} ?",
    ]
    
    for i in range(total_questions):
        word = sample_words[i % len(sample_words)] if sample_words else f"concept_{i+1}"
        question_template = random.choice(question_types)
        
        correct_answer = f"Réponse correcte sur {word}"
        wrong_answers = [
            f"Fausse réponse A sur {word}",
            f"Fausse réponse B sur {word}",
            f"Fausse réponse C sur {word}",
        ]
        
        # Mélanger les choix
        all_choices = [correct_answer] + wrong_answers
        random.shuffle(all_choices)
        
        questions.append({
            "type": "qcm",
            "question": question_template.format(word=word),
            "choices": all_choices,
            "answer": correct_answer,
            "explanation": f"Explication mockée pour la question {i+1}"
        })
    
    return questions


def generate_quiz_from_text(text: str, total_questions: int = 20):
    """
    Appelle le modèle Gemini pour générer un quiz structuré.
    En mode MOCK, génère des questions fictives.
    Retourne une liste de dictionnaires (items).
    """
    # Mode mock activé
    if MOCK_MODE:
        return generate_mock_quiz(text, total_questions)
    
    # Mode production - Appel réel à Gemini
    print(f"🤖 Appel API Gemini - Génération de {total_questions} questions réelles")
    prompt = PROMPT_TEMPLATE.format(texte=text, nb_questions=total_questions)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
            response_json_schema=QuizResponse.model_json_schema()
        )
    )

    try:
        # Validation Pydantic automatique
        quiz = QuizResponse.model_validate_json(response.text)
        return [item.dict() for item in quiz.items]

    except Exception as e:
        print("❌ Erreur de parsing JSON :", e)
        print("Réponse brute :", response.text[:300])
        return []