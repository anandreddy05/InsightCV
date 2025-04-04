# from langchain_chroma import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
# from sqlalchemy.orm import Session
# from fastapi import Depends, HTTPException
# from typing import Annotated
# from database import get_db, SessionLocal
# from models import Resume
# import json

# # Choose your model here
# embedding_model = HuggingFaceEmbeddings(
#     model_name="BAAI/bge-large-en",
#     model_kwargs={'device': 'cuda'},
#     encode_kwargs={'normalize_embeddings': True}
# )

# vector_store = Chroma(
#     persist_directory="chroma_db_store",
#     embedding_function=embedding_model,
#     collection_name="resume_embeddings"  # Add a specific collection name
# )

# # Modified refresh_resume_embeddings function
# def refresh_resume_embeddings(db, resume_id: int = None):
#     if resume_id:
#         vector_store.delete(filter={"resume_id": resume_id})
#     else:
#         # Instead of delete_collection, use this pattern
#         vector_store._collection = None  # Reset the collection reference
#         if hasattr(vector_store, "_persist"):
#             vector_store._persist.delete_collection()
#         vector_store.get_or_create_collection()  # Create a fresh collection
    
#     store_resume_embeddings(db)
#     vector_store.persist()

# db_dependency = Annotated[Session, Depends(get_db)]


# def ensure_json_list(value):
#     if isinstance(value, str):
#         try:
#             return json.loads(value)
#         except Exception:
#             return []
#     elif isinstance(value, list):
#         return value
#     return []


# def get_combined_resume_text(resume: Resume) -> str:
#     sections = []

#     if resume.extracted_text:
#         sections.append(resume.extracted_text)

#     if resume.skills:
#         skills = ensure_json_list(resume.skills)
#         sections.append("Skills: " + ", ".join(skills))

#     for exp in ensure_json_list(resume.experience):
#         role = exp.get("role", "")
#         company = exp.get("company", "")
#         sections.append(f"{role} at {company}")

#     for proj in ensure_json_list(resume.projects):
#         name = proj.get("name", "")
#         tech = ", ".join(proj.get("tech_stack", []))
#         sections.append(f"Project: {name} using {tech}")

#     for edu in ensure_json_list(resume.education):
#         degree = edu.get("degree", "")
#         institution = edu.get("institution", "")
#         sections.append(f"Education: {degree} from {institution}")

#     return "\n".join(sections)


# # Store embeddings in ChromaDB
# def store_resume_embeddings(db: db_dependency):
#     resumes = db.query(Resume).all()
#     for resume in resumes:
#         text = get_combined_resume_text(resume)
#         if not text:
#             continue

#         vector_store.add_texts(
#             texts=[text],
#             metadatas=[{
#                 "resume_id": resume.id,
#                 "user_id": resume.user_id,
#                 "file_path": resume.file_path
#             }]
#         )

# # Score a specific resume
# def get_resume_scores(job_desc: str, resume_id: int, db: db_dependency):
#     resume = db.query(Resume).filter(Resume.id == resume_id).first()
#     if not resume:
#         raise HTTPException(404, "Resume not found")

#     resume_text = get_combined_resume_text(resume)
#     if not resume_text:
#         return 0.0

#     results = vector_store.similarity_search_with_score(
#         job_desc,
#         filter={"resume_id": resume_id}
#     )

#     if not results:
#         return 0.0

#     distance = results[0][1]
#     score = (1 - min(max(distance, 0), 1)) * 100
#     return round(score, 2)


# # Recruiter search
# def search_resumes(job_desc: str, top_n: int = 5):
#     query_embedding = embedding_model.embed_query(job_desc)

#     results = vector_store.similarity_search_by_vector(query_embedding, k=top_n)

#     return [
#         {
#             "resume_id": doc.metadata["resume_id"],
#             "file_path": doc.metadata["file_path"],
#             "match_score": f"{(1 - min(max(score, 0), 1)) * 100:.1f}%"
#         }
#         for doc, score in results
#     ]


# # Test script
# if __name__ == "__main__":
#     job_desc = """
#     We are looking for a Python Developer experienced in LangChain, Hugging Face Transformers, and RAG pipelines 
#     for building cutting-edge Generative AI applications. The ideal candidate should be proficient in:

#     - Python programming
#     - LangChain for building modular LLM workflows
#     - Hugging Face Transformers for NLP tasks
#     - RAG (Retrieval-Augmented Generation) techniques
#     - Git & GitHub for version control
#     - React, HTML, CSS, JavaScript for frontend integration
#     - Matplotlib & Seaborn for data visualization

#     Bonus: experience with FAISS/vector databases and building end-to-end LLM apps.
#     """


#     db = SessionLocal()

#     # Uncomment this line to refresh ALL embeddings
#     refresh_resume_embeddings(db)

#     # Test scoring
#     score = get_resume_scores(job_desc, resume_id=1, db=db)
#     print(f"Resume match score: {score}")
