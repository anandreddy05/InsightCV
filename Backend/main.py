from fastapi import FastAPI
from routers import users,admin,resume,resume_scores
app = FastAPI()

app.include_router(users.router)
app.include_router(admin.router)
app.include_router(resume.router)
app.include_router(resume_scores.router)