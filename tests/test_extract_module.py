# tests/test_extract_module.py

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

SAMPLES_DIR = Path("samples")
SAMPLES_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

from app.extract import extract_text_from_docx

def run_extract_docx_to_markdown():
    """
    Test manuel : extrait le texte d'un vrai fichier .docx et le sauvegarde au format .md
    """
    sample_path = SAMPLES_DIR / "03 [FIQH] - Ijtihad Définition & Conditions.docx"

    if not sample_path.exists():
        print(f"Fichier d’exemple manquant : {sample_path}")
        print("Ajoute un fichier DOCX dans le dossier 'samples/' pour ce test.")
        return

    print(f"Extraction du fichier : {sample_path.name}")

    try:
        text_md = extract_text_from_docx(str(sample_path))
    except Exception as e:
        print("Erreur d’extraction :", e)
        return

    # Sauvegarde du résultat Markdown
    output_path = OUTPUT_DIR / f"{sample_path.stem}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text_md)

    print(f"Extraction réussie → Markdown enregistré dans : {output_path}")
    print("Aperçu du texte extrait :")
    print("-" * 60)
    print(text_md[:600]) 
    print("-" * 60)

if __name__ == "__main__":
    run_extract_docx_to_markdown()
