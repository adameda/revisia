import uuid
import enum
from sqlalchemy import Column, Text, Boolean, DateTime, ForeignKey, Enum, JSON, Float, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .db import Base

# --- Enum pour le type de question ---
class QuestionType(str, enum.Enum):
    qcm = "qcm"
    ouverte = "ouverte"


# --- Table users ---
class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(Text, unique=True, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


# --- Table subjects (matières) ---
class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    color = Column(Text, nullable=False, default="#3B82F6")  # Couleur par défaut (bleu)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="subjects")
    documents = relationship("Document", back_populates="subject")


# --- Table documents ---
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user_id = Column(Text, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="documents")

    subject_id = Column(Text, ForeignKey("subjects.id"), nullable=True)
    subject = relationship("Subject", back_populates="documents")

    questions = relationship("Question", back_populates="document", cascade="all, delete-orphan")


# --- Table questions ---
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    type = Column(Enum(QuestionType), nullable=False)
    question = Column(Text, nullable=False)
    choices = Column(JSON, nullable=True)
    answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    document = relationship("Document", back_populates="questions")
    results = relationship("Result", back_populates="question", cascade="all, delete-orphan")


# --- Table results ---
class Result(Base):
    __tablename__ = "results"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(Text, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), nullable=True)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    evaluation = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, server_default=func.now())

    question = relationship("Question", back_populates="results")
    quiz_session_id = Column(Text, ForeignKey("quiz_sessions.id"), nullable=True)
    quiz_session = relationship("QuizSession", back_populates="results")


# --- Table quiz_sessions ---
class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    score = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    played_at = Column(DateTime, server_default=func.now())

    # Relations
    user = relationship("User", back_populates="quiz_sessions")
    document = relationship("Document")
    results = relationship("Result", back_populates="quiz_session", cascade="all, delete-orphan")
