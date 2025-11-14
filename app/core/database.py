from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from app.core.config import settings

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class JobStatus(str, enum.Enum):
    """Evaluation job status enum"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Document type enum"""
    CV = "cv"
    PROJECT_REPORT = "project_report"


class UploadedDocument(Base):
    """Model for uploaded documents"""
    __tablename__ = "uploaded_documents"
    
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)


class EvaluationJob(Base):
    """Model for evaluation jobs"""
    __tablename__ = "evaluation_jobs"
    
    id = Column(String, primary_key=True, index=True)
    cv_id = Column(String, nullable=False)
    project_report_id = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    
    # CV Evaluation Results
    cv_match_rate = Column(Float, nullable=True)
    cv_feedback = Column(Text, nullable=True)
    
    # Project Evaluation Results
    project_score = Column(Float, nullable=True)
    project_feedback = Column(Text, nullable=True)
    
    # Overall Summary
    overall_summary = Column(Text, nullable=True)
    
    # Detailed Scores (stored as JSON text)
    cv_detailed_scores = Column(Text, nullable=True)
    project_detailed_scores = Column(Text, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()