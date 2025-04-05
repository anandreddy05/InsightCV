from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import SimpleJsonOutputParser
import os
from database import get_db
from models import Resume, UserRole
from .auth import role_required
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

db_dependency = Annotated[Session, Depends(get_db)]

groq_api = os.getenv("GROQ_API_KEY")

model = ChatGroq(
    api_key=groq_api,
    model="llama3-8b-8192",
    temperature=0.3
)

prompt = PromptTemplate(
    template="""
Compare the following job description and resume.

Job Description:
{job_description}

Resume:
{resume_text}

Tasks:
1. Review the resume in context of the job description.
2. Score based on:
    a. Projects (50 pts) — uniqueness and technical difficulty.
    b. Experience (30 pts) — relevance and depth.
    c. CGPA (20 pts) — only consider if resumes are similarly strong.

3. Return only a valid, strict JSON object with the fields:
    - match_score (int)
    - summary (str)
    - file_path (same as {resume_file_path})

⚠️ DO NOT include any commentary, explanation, or markdown.
⚠️ JUST return the JSON object. No breakdown or extra text.

Example:
{{
    "match_score": 85,
    "summary": "Strong technical projects aligned with the role. Great match overall.",
    "file_path": "{resume_file_path}"
}}
""",
    input_variables=["job_description", "resume_text", "resume_file_path"]
)


parser = SimpleJsonOutputParser()
chain = prompt | model | parser


class BestResumesRequest(BaseModel):
    job_description: str


@router.post("/match-best-resumes", dependencies=[Depends(role_required(UserRole.recruiter))])
async def find_best_resume(payload: BestResumesRequest, db: db_dependency):
    job_description = payload.job_description

    resumes = db.query(Resume).all()
    if not resumes:
        return {"error": "No resumes found in the database."}

    scored_resumes = []

    for resume in resumes:
        combined_text = "\n".join([
            resume.education or "",
            resume.experience or "",
            resume.projects or "",
            resume.skills or ""
        ]).strip()

        if not combined_text:
            continue

        try:
            result = chain.invoke({
                "job_description": job_description,
                "resume_text": combined_text,
                "resume_file_path": resume.file_path
            })

            scored_resumes.append({
                "user_id": resume.user_id,
                "resume_id": resume.id,
                "file_path": resume.file_path,
                "match_score": result.get("match_score", 0),
                "summary": result.get("summary", "")
            })
        except Exception as e:
            print(f"Error processing resume ID {resume.id}: {e}")
            continue

    if not scored_resumes:
        return {"error": "No valid resumes were processed by the LLM."}

    best_resume = max(scored_resumes, key=lambda r: r["match_score"])
    return best_resume
