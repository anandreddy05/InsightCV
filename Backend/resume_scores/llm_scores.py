from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import SimpleJsonOutputParser,StrOutputParser
from models import Resume
from database import get_db
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()

db_dependency = Annotated[Session, Depends(get_db)]
groq_api = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api,
                 model="llama3-8b-8192",
                 temperature=0.3)

prompt =PromptTemplate(
    template="""
    Compare the following job description and resume. 

    Job Description:
    {job_description}

    Resume:
    {resume_text}

    Tasks:
    1. List top matching keywords and skills.
    2. List missing or weakly mentioned skills that the job requires.
    3. Estimate a match percentage (0-100%). (Be very hard on the resume)
    4. Provide resume improvement suggestions based on the job description.
    5. If there are any errors or typos make sure to provide to the user.
    
    Perform these tasks very accurately and strictly.
    
    Respond in **strict** JSON format as:
    {
    "match_keywords": [...],
    "missing_skills": [...],
    "match_score": int, 
    "suggestions": "1.Suggestion 1
                    2.Suggestion 2"
                    3.
                    4.
    }               

    """,
    input_variables=["job_description","resume_text"]    
    )
parser = SimpleJsonOutputParser()

def llm_score_user(job_desc: str, db: db_dependency, resume_id: int):
    resumes = db.query(Resume).filter(Resume.id == resume_id).all()
    if not resumes:
        return {"error": "No resumes found"}

    chain = prompt | model | parser

    results = []
    for resume in resumes:
        if resume.extracted_text and resume.extracted_text.strip():
            result = chain.invoke({
                "job_description": job_desc,
                "resume_text": resume.extracted_text
            })
            results.append({
                "resume_id": resume.id,
                "file_path": resume.file_path,
                **result
            })

    return results