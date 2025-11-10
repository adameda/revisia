# app/llm.py

import os
import json
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types 

# Charger les variables d’environnement
load_dotenv()

# Initialiser le client Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"


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
**INSTRUCTIONS STRICTES :**

Tu es un générateur de quiz pédagogique expert. Ta mission est de créer un ensemble de questions à choix multiples (QCM) basées **uniquement** sur le cours fourni ci-dessous.

**Règle absolue :**
- N’utilise **aucune connaissance externe**.
- Chaque question et sa réponse correcte doivent être **directement justifiables** par le cours donné.

**TÂCHES :**
1. Génère **{nb_questions} questions QCM** pour enrichir une base de données.
2. Le jeu de questions doit **couvrir tout le cours** de manière équilibrée : définitions, concepts, noms, dates, classifications.
3. Chaque question doit :
   - être courte et claire ;
   - avoir **4 choix plausibles** ;
   - contenir **une seule réponse correcte** ;
   - éviter les formulations ambiguës ou évidentes.
4. Les réponses doivent être précises.

TEXTE À ANALYSER :
<<<
{texte}
<<<
"""


def generate_quiz_from_text(text: str, total_questions: int = 20):
    """
    Appelle le modèle Gemini pour générer un quiz structuré.
    Retourne une liste de dictionnaires (items).
    """
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