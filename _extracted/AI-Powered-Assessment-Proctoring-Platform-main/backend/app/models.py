from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student")  # "student" or "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)

    exam = relationship("Exam", back_populates="questions")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    violation_type = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_data = Column(Text, nullable=False)  # JSON: locked questions + shuffled options
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="in_progress")  # in_progress / submitted / terminated


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)
    interview_type = Column(String, nullable=False, default="technical")
    status = Column(String, nullable=False, default="scheduled")
    allowlist = Column(Text, nullable=True, default="[]")
    started_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    candidate_consent = Column(String, default="false")
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    events = relationship("InterviewEvent", back_populates="interview", cascade="all, delete-orphan")
    connections = relationship("InterviewDeviceConnection", back_populates="interview", cascade="all, delete-orphan")


class InterviewEvent(Base):
    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    source = Column(String, nullable=False, default="browser")
    event_type = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    app_name = Column(String, nullable=True)
    process_name = Column(String, nullable=True)
    window_title = Column(String, nullable=True)
    tab_id = Column(Integer, nullable=True)
    risk_score = Column(Integer, default=0)
    is_suspicious = Column(String, default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("InterviewSession", back_populates="events")


class InterviewDeviceConnection(Base):
    __tablename__ = "interview_device_connections"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    device_type = Column(String, nullable=False)
    connected = Column(String, default="false")
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("InterviewSession", back_populates="connections")