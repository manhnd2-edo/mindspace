import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
from app.routers import report, knowledge, airtable, sentiment, chat

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("CTS Operations Agent started")
    yield
    stop_scheduler()
    logger.info("CTS Operations Agent stopped")


app = FastAPI(
    title="CTS Operations Agent",
    description="AI operations agent for VNGGames CTS social media team",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(report.router, prefix="/report", tags=["Report Generator"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
app.include_router(airtable.router, prefix="/airtable", tags=["Airtable Monitor"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["Sentiment Tracker"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
