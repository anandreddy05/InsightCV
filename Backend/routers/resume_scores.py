from pydantic import BaseModel
from database import get_db
from models import Resume
from fastapi import Depends,APIRouter,HTTPException,status
from typing import Annotated
from sqlalchemy.orm import Session
from resume_scores.llm_scores import llm_score
from resume_scores.hybrid_scoring import hybrid_match_score

db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/resume_scores",
    tags=["resume_scores"]
)

class Description(BaseModel):
    job_description: str
    
@router.post("/get_score/{resume_id}")
async def score(db:db_dependency,desc:Description,resume_id:int):
    resume_instance = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No resume found")
    llm_result = llm_score(job_desc=desc.job_description,resume_id=resume_id,db=db)
    similarity_result = hybrid_match_score(job_desc=desc.job_description,resume_text=resume_instance.extracted_text)
    return {"resume_id":resume_id,
            "similarity_result":similarity_result,
            "llm_result":llm_result
            }

