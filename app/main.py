from dotenv import load_dotenv
load_dotenv()  # load .env before anything else

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.researcher import researcher_job
from app.synthesizer import synthesize_from_sources

app = FastAPI(title="RICE-Kano Agent Prototype")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask")
async def ask(question: str = Form(...)):
    query = question + " RICE Kano model prioritization comparison"
    sources = researcher_job(query, top_k_sites=5)
    try:
        final_answer = synthesize_from_sources(question, sources)
        return JSONResponse({"ok": True, **final_answer})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)), reload=True)
