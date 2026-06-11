from fastapi import APIRouter

from app.modules.airtable_monitor import get_records_summary, run_daily_check

router = APIRouter()


@router.post("/check")
async def trigger_check():
    issues = await run_daily_check()
    return {"issues_found": len(issues), "issues": issues}


@router.get("/summary")
async def summary():
    return await get_records_summary()
