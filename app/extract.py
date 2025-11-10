from markitdown import MarkItDown

def extract_text_from_docx(file_path: str) -> str:
    """
    Extrait le texte d'un fichier DOCX et le convertit en Markdown.
    Retourne une chaîne de caractères.
    """
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content.strip()
