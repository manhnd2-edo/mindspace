import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
from app.routers import report, knowledge, airtable, sentiment, chat, agents

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("NOVA started")
    yield
    stop_scheduler()
    logger.info("NOVA stopped")


app = FastAPI(
    title="NOVA",
    description="No-touch Operations & Virtual Assistant for VNGGames CTS social media team",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(report.router, prefix="/report", tags=["Report Generator"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
app.include_router(airtable.router, prefix="/airtable", tags=["Airtable Monitor"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["Sentiment Tracker"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(agents.router)

_STATIC = Path(__file__).parent.parent / "static"
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(str(_STATIC / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
