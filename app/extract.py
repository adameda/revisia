from markitdown import MarkItDown

def extract_text_from_docx(file_path: str) -> str:
    """
    Extrait le texte d'un fichier DOCX et le convertit en Markdown.
    Retourne une chaîne de caractères.
    """
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content.strip()

def count_words(text: str) -> int:
    """
    Compte le nombre de mots dans un texte.
    """
    return len(text.split())

def get_preview(text: str, max_chars: int = 200) -> str:
    """
    Retourne un aperçu du texte (premiers caractères).
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."
