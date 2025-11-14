from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document type enumeration"""
    CV = "cv"
    PROJECT_REPORT = "project_report"


# Upload Schemas
class UploadResponse(BaseModel):
    """Response after uploading a document"""
    id: str
    filename: str
    document_type: str
    uploaded_at: datetime
    file_size: int
    
    class Config:
        from_attributes = True


class UploadBatchResponse(BaseModel):
    """Response after uploading both CV and project report"""
    cv: UploadResponse
    project_report: UploadResponse


# Evaluation Schemas
class EvaluationRequest(BaseModel):
    """Request to start evaluation"""
    cv_id: str = Field(..., description="ID of uploaded CV document")
    project_report_id: str = Field(..., description="ID of uploaded project report")
    job_title: str = Field(..., description="Job title for evaluation")


class EvaluationQueuedResponse(BaseModel):
    """Response when evaluation is queued"""
    id: str
    status: JobStatus
    message: Optional[str] = "Evaluation queued successfully"


class CVDetailedScores(BaseModel):
    """Detailed CV evaluation scores"""
    technical_skills_match: float = Field(..., ge=1, le=5)
    experience_level: float = Field(..., ge=1, le=5)
    relevant_achievements: float = Field(..., ge=1, le=5)
    cultural_fit: float = Field(..., ge=1, le=5)


class ProjectDetailedScores(BaseModel):
    """Detailed project evaluation scores"""
    correctness: float = Field(..., ge=1, le=5)
    code_quality: float = Field(..., ge=1, le=5)
    resilience: float = Field(..., ge=1, le=5)
    documentation: float = Field(..., ge=1, le=5)
    creativity: float = Field(..., ge=1, le=5)


class EvaluationResult(BaseModel):
    """Complete evaluation result"""
    cv_match_rate: float = Field(..., ge=0, le=1, description="CV match rate (0-1)")
    cv_feedback: str = Field(..., description="Feedback on CV evaluation")
    project_score: float = Field(..., ge=1, le=5, description="Project score (1-5)")
    project_feedback: str = Field(..., description="Feedback on project evaluation")
    overall_summary: str = Field(..., description="Overall evaluation summary")
    
    # Optional detailed scores
    cv_detailed_scores: Optional[CVDetailedScores] = None
    project_detailed_scores: Optional[ProjectDetailedScores] = None


class EvaluationResponse(BaseModel):
    """Response for evaluation status check"""
    id: str
    status: JobStatus
    result: Optional[EvaluationResult] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Internal Processing Schemas
class ParsedCV(BaseModel):
    """Parsed CV data structure"""
    raw_text: str
    structured_data: Dict[str, Any] = {}
    sections: Dict[str, str] = {}


class ParsedProjectReport(BaseModel):
    """Parsed project report data structure"""
    raw_text: str
    structured_data: Dict[str, Any] = {}
    sections: Dict[str, str] = {}


class CVEvaluationResult(BaseModel):
    """Intermediate CV evaluation result"""
    match_rate: float
    feedback: str
    detailed_scores: CVDetailedScores


class ProjectEvaluationResult(BaseModel):
    """Intermediate project evaluation result"""
    score: float
    feedback: str
    detailed_scores: ProjectDetailedScores


# Error Schemas
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int = 400