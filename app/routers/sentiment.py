from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.sentiment_tracker import generate_sentiment_report

router = APIRouter()


class SentimentRequest(BaseModel):
    product: str = "PUBG Mobile VN"
    start: date | None = None
    end: date | None = None
    send_to_teams: bool = True


@router.post("/report")
async def sentiment_report(req: SentimentRequest):
    report = await generate_sentiment_report(
        start=req.start,
        end=req.end,
        product=req.product,
        send_to_teams=req.send_to_teams,
    )
    return {"report": report}
