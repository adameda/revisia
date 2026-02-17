import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Récupère l'URL de la base depuis l'environnement (PostgreSQL)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL n'est pas définie. "
        "Vérifie ton fichier .env ou tes variables d'environnement."
    )

# Crée l'engine SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db(app=None):
    """
    Initialise la base (crée les tables si besoin).
    """
    import logging
    logger = logging.getLogger("app.db")
    logger.info(f"Base de données : {DATABASE_URL}")

    from .models import question_type_enum
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(12345)"))
        question_type_enum.create(bind=engine, checkfirst=True)
        Base.metadata.create_all(bind=engine)
        conn.commit()