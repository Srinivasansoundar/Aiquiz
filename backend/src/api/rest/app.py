from fastapi import FastAPI
from src.api.rest.routes.quiz_routes import router as quiz_router
from src.api.rest.middleware.cors import setup_cors

def create_app():
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="AI Quiz API",
        description="Interactive quiz system with LangGraph integration",
        version="1.0.0"
    )
    setup_cors(app)
    
    # Register routers
    app.include_router(quiz_router)
    
    # Health check endpoint
    
    return app
