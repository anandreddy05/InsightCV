from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from llm_models.extractor import extract_resume_data
from .users import get_current_user
from typing import Annotated, List, Dict, Optional
from models import Resume, User
from pydantic import BaseModel, ConfigDict, Field
import json
import os
from datetime import datetime
import uuid

router = APIRouter(
    prefix="/resume",
    tags=["resume"]
)

db_dependency = Annotated[Session, Depends(get_db)]

class ExperienceItem(BaseModel):
    company: str
    role: str
    years: str

class ProjectItem(BaseModel):
    project_name: str
    tech_stack: List[str]
    description: str

class EducationItem(BaseModel):
    institution: str
    degree: str
    years: str
    cgpa: Optional[str] = None

class ResumeResponse(BaseModel):
    user_id: int
    file_path: str
    extracted_text: str = Field(..., description="Name extracted from resume")
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


@router.post("/upload_resume", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    db: db_dependency,
    user: User = Depends(get_current_user), 
    file: UploadFile = File(...)
):
    try:
        # Ensure upload directory exists
        os.makedirs("uploads/resumes", exist_ok=True)
        
        # Extract data from resume
        extracted_data = extract_resume_data(file)
        
        if not extracted_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract resume data"
            )

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join("uploads/resumes", unique_filename)
        
        # Create resume record with JSON-converted fields
        resume = Resume(
            user_id=user.id,
            file_path=file_path,
            extracted_text=extracted_data.get("name", ""),
            skills=json.dumps(extracted_data.get("skills", [])),
            experience=json.dumps(extracted_data.get("experience", [])),
            projects=json.dumps(extracted_data.get("projects", [])),
            education=json.dumps(extracted_data.get("education", []))
        )
        
        db.add(resume)
        db.commit()
        db.refresh(resume)

        # Convert JSON strings back to Python objects for the response
        return ResumeResponse(
            user_id=resume.user_id,
            file_path=resume.file_path,
            extracted_text=resume.extracted_text or "No name extracted",
            skills=json.loads(resume.skills),
            experience=json.loads(resume.experience),
            projects=json.loads(resume.projects),
            education=json.loads(resume.education),
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing resume: {str(e)}"
        )