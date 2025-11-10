import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
SessionLocal = sessionmaker()

def init_db(app):
    print("📂 DATABASE_URL utilisé :", app.config["DATABASE_URL"])
    print("📁 Fichier absolu :", os.path.abspath(app.config["DATABASE_URL"].replace("sqlite:///", "")))
    engine = create_engine(app.config["DATABASE_URL"], echo=True)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)