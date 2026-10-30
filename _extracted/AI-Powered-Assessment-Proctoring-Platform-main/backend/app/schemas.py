import json

from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import List, Dict

# What the frontend sends us when signing up
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "student"  # defaults to student unless specified

# What the frontend sends us when logging in
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# What we send back to the frontend after signup/login (never includes password!)
class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True

# What we send back after successful login
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
# ----------- QUESTION SCHEMAS -----------

class QuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str  # "A", "B", "C", or "D"

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str

    class Config:
        from_attributes = True

# Version sent to students - hides the correct answer!
class QuestionForStudent(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str

    class Config:
        from_attributes = True

# ----------- EXAM SCHEMAS -----------

class ExamCreate(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    questions: List[QuestionCreate]
    
class ExamResponse(BaseModel):
    id: int
    title: str
    description: str | None
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    questions: List[QuestionResponse]

    class Config:
        from_attributes = True

# Version sent to students when they start an exam - no correct answers visible
class ExamForStudent(BaseModel):
    id: int
    title: str
    description: str | None
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    questions: List[QuestionForStudent]

    class Config:
        from_attributes = True

# ----------- SUBMISSION SCHEMAS -----------
# ----------- SUBMISSION SCHEMAS -----------

class SubmissionCreate(BaseModel):
    answers: Dict[int, str]  # {question_id: "A"} - student's selected answers

class SubmissionResponse(BaseModel):
    id: int
    exam_id: int
    score: int
    total_questions: int
    submitted_at: datetime

    class Config:
        from_attributes = True
        
        # ----------- VIOLATION SCHEMAS -----------

class ViolationCreate(BaseModel):
    violation_type: str
    details: str | None = None

class ViolationResponse(BaseModel):
    id: int
    violation_type: str
    details: str | None
    created_at: datetime

class Config:
    from_attributes = True
        
class ViolationWithStudent(BaseModel):
    id: int
    violation_type: str
    details: str | None
    created_at: datetime
    student_id: int

    class Config:
        from_attributes = True


# ----------- INTERVIEW SCHEMAS -----------

class InterviewSessionCreate(BaseModel):
    candidate_name: str
    candidate_email: EmailStr
    interview_type: str = "technical"
    allowlist: List[str] = []
    status: str = "scheduled"
    started_at: datetime | None = None
    ends_at: datetime | None = None


class InterviewSessionResponse(BaseModel):
    id: int
    candidate_name: str
    candidate_email: str
    interview_type: str
    status: str
    allowlist: List[str]
    candidate_consent: bool
    consent_timestamp: datetime | None = None
    started_at: datetime | None = None
    ends_at: datetime | None = None
    created_by: int
    created_at: datetime
    last_seen_at: datetime | None = None

    @validator("allowlist", pre=True)
    def decode_allowlist(cls, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []
        return value if isinstance(value, list) else []

    class Config:
        from_attributes = True


class InterviewConsentUpdate(BaseModel):
    candidate_consent: bool
    required_components: List[str] = []


class InterviewEventCreate(BaseModel):
    event_type: str
    details: str | None = None
    url: str | None = None
    app_name: str | None = None
    process_name: str | None = None
    window_title: str | None = None
    tab_id: int | None = None


class InterviewEventResponse(BaseModel):
    id: int
    interview_id: int
    source: str
    event_type: str
    details: str | None
    url: str | None
    app_name: str | None
    process_name: str | None
    window_title: str | None
    tab_id: int | None
    risk_score: int
    is_suspicious: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewDeviceStatusUpdate(BaseModel):
    device_type: str
    connected: bool


class InterviewDeviceStatusResponse(BaseModel):
    id: int
    interview_id: int
    device_type: str
    connected: bool
    last_seen_at: datetime

    class Config:
        from_attributes = True


class InterviewRiskResponse(BaseModel):
    interview_id: int
    score: int
    level: str
    reasons: List[str]
    suspicious_event_count: int
    event_count: int
    timeline: List[str]


class InterviewReportResponse(BaseModel):
    interview: InterviewSessionResponse
    connection_status: Dict[str, bool]
    risk: InterviewRiskResponse
    events: List[InterviewEventResponse]