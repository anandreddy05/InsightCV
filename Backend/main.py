from fastapi import FastAPI
from routers import admin,recruiter,login, user
app = FastAPI()

app.include_router(login.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(recruiter.router)