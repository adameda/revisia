import uuid
import enum
import random
import string
from sqlalchemy import Boolean, Column, Text, DateTime, ForeignKey, Enum as SAEnum, JSON, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .db import Base

# --- Enum pour le type de question ---

# --- Enum pour le type de question (PostgreSQL) ---
class QuestionType(str, enum.Enum):
    qcm = "qcm"
    ouverte = "ouverte"

# Déclaration explicite de l'ENUM SQLAlchemy pour PostgreSQL
question_type_enum = SAEnum(
    QuestionType,
    name="questiontype",
    create_type=False  # On gère la création manuellement
)


# --- Helper pour générer un code d'invitation unique ---
def generate_invite_code(length=6):
    """Génère un code d'invitation aléatoire au format REV-XXXXXX"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=length))
    return f"REV-{code}"


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
    owned_groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Group.owner_id")
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")

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
    group_links = relationship("GroupSubject", back_populates="subject", cascade="all, delete-orphan")


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
    quiz_sessions = relationship(
        "QuizSession",
        back_populates="document",
        cascade="all, delete-orphan"
    )


# --- Table questions ---
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    type = Column(question_type_enum, nullable=False)
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


# --- Table quiz_generations (compteur de générations par user/jour) ---
class QuizGeneration(Base):
    __tablename__ = "quiz_generations"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")


# --- Table quiz_sessions ---
class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    document_id = Column(Text, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    played_at = Column(DateTime, server_default=func.now())

    # Relations
    user = relationship("User", back_populates="quiz_sessions")
    document = relationship("Document", back_populates="quiz_sessions", passive_deletes=True)
    results = relationship("Result", back_populates="quiz_session", cascade="all, delete-orphan")


# --- Table groups (groupes/classes) ---
class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    invite_code = Column(Text, unique=True, nullable=False)
    owner_id = Column(Text, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", back_populates="owned_groups", foreign_keys=[owner_id])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    subjects = relationship("GroupSubject", back_populates="group", cascade="all, delete-orphan")


# --- Table group_members (membres des groupes) ---
class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(Text, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    __table_args__ = (
        # Contrainte d'unicité : un utilisateur ne peut rejoindre un groupe qu'une seule fois
        # Note: SQLAlchemy utilise __table_args__ pour les contraintes de table
    )


# --- Table group_subjects (matières liées aux groupes) ---
class GroupSubject(Base):
    __tablename__ = "group_subjects"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(Text, ForeignKey("groups.id"), nullable=False)
    subject_id = Column(Text, ForeignKey("subjects.id"), nullable=False)
    added_at = Column(DateTime, server_default=func.now())

    group = relationship("Group", back_populates="subjects")
    subject = relationship("Subject", back_populates="group_links")


# --- Table events (événements/compétitions) ---
class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    group_id = Column(Text, ForeignKey("groups.id"), nullable=False)
    subject_id = Column(Text, ForeignKey("subjects.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    group = relationship("Group")
    subject = relationship("Subject")
    quizzes = relationship("EventQuiz", back_populates="event", cascade="all, delete-orphan", order_by="EventQuiz.quiz_number")
    participations = relationship("EventParticipation", back_populates="event", cascade="all, delete-orphan")
    
    def get_status(self):
        """Retourne le statut de l'événement : 'future', 'active', 'ended'"""
        from datetime import datetime
        now = datetime.now()
        
        if now < self.start_date:
            return 'future'
        elif now > self.end_date:
            return 'ended'
        else:
            return 'active'


# --- Table event_quizzes (quiz d'un événement) ---
class EventQuiz(Base):
    __tablename__ = "event_quizzes"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(Text, ForeignKey("events.id"), nullable=False)
    quiz_number = Column(Integer, nullable=False)  # 1 à 5
    questions = Column(JSON, nullable=False)  # Liste des IDs des questions
    created_at = Column(DateTime, server_default=func.now())
    
    event = relationship("Event", back_populates="quizzes")
    participations = relationship("EventParticipation", back_populates="quiz", cascade="all, delete-orphan")


# --- Table event_participations (participation d'un étudiant à un quiz d'événement) ---
class EventParticipation(Base):
    __tablename__ = "event_participations"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(Text, ForeignKey("events.id"), nullable=False)
    quiz_id = Column(Text, ForeignKey("event_quizzes.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    correct_count = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False)
    time_spent = Column(Integer, nullable=True)  # en secondes
    answers = Column(JSON, nullable=False)  # Détails des réponses
    completed_at = Column(DateTime, server_default=func.now())
    
    event = relationship("Event", back_populates="participations")
    quiz = relationship("EventQuiz", back_populates="participations")
    user = relationship("User")
