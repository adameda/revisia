# tests/test_llm.py

import os
import sys
import json
import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from app.llm import generate_quiz_from_text

OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Texte de test plus riche et structuré
TEXT = """
La révolution industrielle débute en Angleterre à la fin du XVIIIe siècle.
Elle est marquée par l'invention de la machine à vapeur par James Watt,
l'essor des usines textiles, et le développement du chemin de fer.

Cette période transforme profondément la société : l'urbanisation s'accélère,
de nouvelles classes sociales apparaissent (bourgeoisie industrielle et prolétariat),
et les conditions de travail dans les usines sont souvent très difficiles.

Parallèlement, des penseurs comme Karl Marx et Friedrich Engels critiquent
les inégalités créées par le capitalisme industriel. Leurs idées donneront naissance
au socialisme et au marxisme, qui influenceront durablement la politique mondiale.
"""

def main():
    print("🚀 Test de génération de quiz via Gemini...\n")

    quiz_items = generate_quiz_from_text(TEXT, total_questions=10)
    print(f"{len(quiz_items)} questions générées.\n")

    if not quiz_items:
        print("❌ Aucune question générée — vérifie ta clé API ou ton modèle.")
        return

    # Afficher un échantillon
    for i, q in enumerate(quiz_items[:3], 1):
        print(f"{i}. {q.get('question')}")
        print(f"   Choix: {q.get('choices')}")
        print(f"   Réponse: {q.get('answer')}\n")

    # Sauvegarde complète du quiz
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"quiz_revolution_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quiz_items, f, ensure_ascii=False, indent=2)

    print(f"📁 Résultat complet enregistré dans {output_path}")

if __name__ == "__main__":
    main()
