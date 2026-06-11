from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.report_generator import generate_report, ReportPeriod

router = APIRouter()


class ReportRequest(BaseModel):
    period: ReportPeriod = "weekly"
    product: str = "PUBG Mobile VN"
    start: date | None = None
    end: date | None = None
    send_to_teams: bool = True


@router.post("/generate")
async def create_report(req: ReportRequest):
    text = await generate_report(
        period=req.period,
        product=req.product,
        start=req.start,
        end=req.end,
        send_to_teams=req.send_to_teams,
    )
    return {"report": text}
