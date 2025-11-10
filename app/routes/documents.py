import os
import uuid
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from ..db import SessionLocal
from ..models import Document
from ..extract import extract_text_from_docx

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@bp.route("/upload", methods=["POST"])
@login_required
def upload_document():
    """
    Upload d’un fichier DOCX, extraction du texte et stockage dans la base.
    Le document est associé à l’utilisateur connecté.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Aucun fichier envoyé"}), 400

    filename = secure_filename(file.filename)
    if not filename.endswith(".docx"):
        return jsonify({"error": "Format non supporté"}), 400

    # Sauvegarde temporaire du fichier
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Extraction du texte
    text_content = extract_text_from_docx(file_path)

    # Enregistrement dans la base
    session = SessionLocal()
    document = Document(
        id=str(uuid.uuid4()),
        title=filename,
        content=text_content,
        user_id=current_user.id,  # association directe à l'utilisateur connecté
    )
    session.add(document)
    session.commit()

    # Sauvegarder les valeurs avant de fermer la session
    doc_id = document.id
    doc_title = document.title
    session.close()

    return jsonify({
        "message": "Document enregistré avec succès",
        "document_id": doc_id,
        "title": doc_title
    }), 201


@bp.route("/<string:document_id>", methods=["DELETE"])
@login_required
def delete_document(document_id):
    """
    Supprime un document appartenant à l'utilisateur connecté.
    Les questions et résultats liés seront supprimés automatiquement (cascade SQLAlchemy).
    """
    session = SessionLocal()
    try:
        document = session.get(Document, document_id)
        if not document:
            session.close()
            return jsonify({"error": "Document introuvable"}), 404

        # Vérification que le document appartient bien à l'utilisateur connecté
        if document.user_id != current_user.id:
            session.close()
            return jsonify({"error": "Non autorisé"}), 403

        session.delete(document)
        session.commit()
        session.close()

        return jsonify({"message": f"Document supprimé avec succès"}), 200

    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"error": str(e)}), 500