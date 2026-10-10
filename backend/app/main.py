from fastapi import FastAPI
from sqlalchemy import text
from app.api.qa import router as qa_router
from app.api.fixed_rag import router as fixed_rag_router
from app.api.ablation import router as ablation_router
from app.api.ablation_context_selection import router as ablation_context_router
from app.api.documents import router as documents_router
from app.api.devops import router as devops_router
from app.database import Base, engine
from app.models import User

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Lumora API",
    description="Agentic RAG-Based Personalized Learning Platform",
    version="0.1.0",
)

app.include_router(qa_router)
app.include_router(fixed_rag_router)
app.include_router(ablation_router)
app.include_router(ablation_context_router)
app.include_router(documents_router)
app.include_router(devops_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "lumora-backend",
    }


@app.get("/health/db")
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "postgresql",
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(e),
        }


@app.get("/")
def root():
    return {
        "message": "Welcome to Lumora API",
        "version": "0.1.0",
    }
