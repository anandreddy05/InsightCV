from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from llm_models.extractor import extract_resume_data
from .users import get_current_user
from typing import Annotated, List, Dict, Optional
from models import Resume, User, UserRole
from pydantic import BaseModel, ConfigDict, Field
import json
import os
from datetime import datetime
from .users import role_required

router = APIRouter(
    prefix="/resume",
    tags=["resume"]
)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)]


UPLOAD_DIR = "uploaded/resumes"  

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
    extracted_text: str
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


@router.get("/get_resume")
async def get_user_resumes(
    db:db_dependency,
    user: User = Depends(get_current_user)
):
    resume_instance = db.query(Resume).filter(Resume.user_id == user.id).all()
    if not resume_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Resume Not Found")
    return resume_instance

@router.post("/upload_resume", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    db: db_dependency,
    user: User = Depends(get_current_user), 
    file: UploadFile = File(...)
):
    try:
        extracted_data = extract_resume_data(file)
        if not extracted_data:
            raise HTTPException(status_code=400, detail="Failed to extract resume data")

        resume = Resume(
            user_id=user.id,
            file_path="",  
            extracted_text=extracted_data.get("name", ""),
            skills=json.dumps(extracted_data.get("skills", [])),
            experience=json.dumps(extracted_data.get("experience", [])),
            projects=json.dumps(extracted_data.get("projects", [])),
            education=json.dumps(extracted_data.get("education", []))
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)  

        #  uniquee file path using resume.id and user_name
        os.makedirs(UPLOAD_DIR, exist_ok=True)  
        file_ext = os.path.splitext(file.filename)[1]  
        unique_filename = f"resume_{resume.id}_{user.full_name}{file_ext}"  
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        #  Save file with  unique file name
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        #  Update the database with the  file path
        resume.file_path = file_path
        db.commit()
        db.refresh(resume)

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
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@router.delete(
    "/delete-resume/{resume_id}",
    dependencies=[Depends(role_required(UserRole.user))],
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_resume(
    db: db_dependency,
    resume_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
):
    resume_instance = db.query(Resume).filter(Resume.id == resume_id).first()

    if not resume_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    if resume_instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this resume"
        )

    db.delete(resume_instance)
    db.commit()