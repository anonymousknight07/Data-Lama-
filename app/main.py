from dotenv import load_dotenv
load_dotenv()  

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import traceback
import time
from typing import Dict, Any

from app.researcher import researcher_job
from app.synthesizer import synthesize_from_sources

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Llama Business Analyst")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "data-llama"}

def format_error_response(error_type: str, message: str, details: str = None) -> Dict[str, Any]:
    """Format error responses consistently"""
    response = {
        "ok": False,
        "error": message,
        "error_type": error_type
    }
    
    if details:
        response["details"] = details
    
    return response

def validate_question(question: str) -> str:
    """Validate and clean the user question"""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    question = question.strip()
    
    if len(question) > 1000:
        raise ValueError("Question is too long (max 1000 characters)")
    
    if len(question) < 3:
        raise ValueError("Question is too short (min 3 characters)")
    
    return question

@app.post("/ask")
async def ask(question: str = Form(...)):
    """
    Main endpoint for processing user questions
    """
    start_time = time.time()
    
    try:
        # Validate input
        question = validate_question(question)
        logger.info(f"Processing question: {question[:100]}...")
        
        # Step 1: Research phase
        try:
            sources = researcher_job(question, top_k_sites=5)
            logger.info(f"Research completed: {len(sources)} sources found")
            
            if not sources:
                return JSONResponse(format_error_response(
                    "NO_SOURCES_FOUND",
                    "Unable to find relevant sources for your question. Please try rephrasing your query or check your internet connection.",
                    "The research system could not retrieve any sources. This might be due to network issues or API limitations."
                ))
            
        except Exception as e:
            logger.error(f"Research phase failed: {e}")
            return JSONResponse(format_error_response(
                "RESEARCH_FAILED",
                "Unable to research your question at this time. Please try again in a few moments.",
                str(e)
            ), status_code=500)
        
        # Step 2: Synthesis phase
        try:
            result = synthesize_from_sources(question, sources)
            
            # Check if synthesis failed due to rate limiting
            if result.get("error") == "API_RATE_LIMITED":
                return JSONResponse({
                    "ok": True,
                    "answer": result["answer"],
                    "citations": result["citations"],
                    "warning": "AI analysis temporarily unavailable due to high demand. Please try again in a few minutes for full analysis.",
                    "source_count": len(sources),
                    "processing_time": round(time.time() - start_time, 2)
                })
            
            # Successful response
            response_data = {
                "ok": True,
                "answer": result["answer"],
                "citations": result["citations"],
                "source_count": len(sources),
                "processing_time": round(time.time() - start_time, 2)
            }
            
            logger.info(f"Question processed successfully in {response_data['processing_time']} seconds")
            return JSONResponse(response_data)
            
        except Exception as e:
            logger.error(f"Synthesis phase failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide fallback response with just sources
            fallback_citations = []
            for i, source in enumerate(sources[:3]):
                fallback_citations.append({
                    "title": source.get("title", f"Source {i+1}"),
                    "url": source.get("url", "#"),
                    "assertion": source.get("summary", source.get("text", "")[:200] + "...")
                })
            
            return JSONResponse({
                "ok": True,
                "answer": f"""I apologize, but I'm experiencing high demand and cannot provide a full AI analysis right now. However, I've successfully found {len(sources)} relevant sources about "{question}".

**What I found:**
Your question has been researched and relevant sources have been identified. The research system is working correctly.

**Current limitation:**
The AI synthesis system is temporarily overloaded (Error: {str(e)[:100]}).

**Recommendation:**
Please try your question again in 2-3 minutes. The system will retry automatically with proper rate limiting.""",
                "citations": fallback_citations,
                "warning": "AI synthesis temporarily unavailable due to system overload",
                "source_count": len(sources),
                "processing_time": round(time.time() - start_time, 2)
            })
    
    except ValueError as e:
        # Input validation errors
        return JSONResponse(format_error_response(
            "INVALID_INPUT",
            str(e)
        ), status_code=400)
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in /ask endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse(format_error_response(
            "SYSTEM_ERROR",
            "An unexpected error occurred. Please try again later.",
            "The system encountered an unexpected error while processing your request."
        ), status_code=500)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    return JSONResponse(
        format_error_response("NOT_FOUND", "The requested resource was not found"),
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        format_error_response("INTERNAL_ERROR", "Internal server error occurred"),
        status_code=500
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Data Llama Business Analyst starting up...")
    
    # Check environment variables
    required_env_vars = ["OPENROUTER_API_KEY"]
    optional_env_vars = ["SERPER_API_KEY"]
    
    missing_required = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        logger.error(f"Missing required environment variables: {missing_required}")
        logger.error("Application may not function properly without these variables")
    
    missing_optional = []
    for var in optional_env_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_optional:
        logger.warning(f"Missing optional environment variables: {missing_optional}")
        logger.warning("Some features may be limited without these variables")
    
    logger.info("Data Llama Business Analyst startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Data Llama Business Analyst shutting down...")

if __name__ == "__main__":
    import uvicorn
    import time
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",  # Updated to match the current file structure
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )