"""FastAPI app. Same six endpoints as the PolymathApi interface in frontend/src/api/index.ts.

Run from backend/:  uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, service
from .config import BUILD, CORS_ORIGINS
from .lenses import get_lens
from .models import AskRequest, AskResult, CrossLensLink, Digest, FeedbackEvent, Lens, SystemStatus


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Polymath API", version="0.1.0", lifespan=lifespan)
# Any localhost port is allowed so Vite can pick a free one; extra origins come from CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "build": BUILD}


@app.get("/lenses", response_model=list[Lens])
def get_lenses():
    return service.lenses()


@app.get("/lenses/{lens_id}/digest", response_model=Digest)
def get_digest(lens_id: str):
    result = service.digest(lens_id)
    if result is None:
        raise HTTPException(404, f"Unknown lens: {lens_id}")
    return result


@app.post("/ask", response_model=AskResult)
def post_ask(req: AskRequest):
    if req.lens_id and not get_lens(req.lens_id):
        raise HTTPException(404, f"Unknown lens: {req.lens_id}")
    return service.ask(req.question, req.lens_id)


@app.post("/feedback", status_code=204)
def post_feedback(event: FeedbackEvent):
    service.save_feedback(event)


@app.get("/links", response_model=list[CrossLensLink])
def get_links(lens: str, limit: int = 3):
    return service.links(lens, limit)


@app.get("/status", response_model=SystemStatus)
def get_status():
    return service.status()
