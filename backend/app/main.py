from fastapi import FastAPI

app = FastAPI(
    title="Lumora API",
    description="Agentic RAG-Based Personalized Learning Platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "lumora-backend",
    }


@app.get("/")
def root():
    return {
        "message": "Welcome to Lumora API",
        "version": "0.1.0",
    }
