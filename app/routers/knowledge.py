from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.knowledge_base import (
    add_entry,
    delete_entry,
    generate_social_plan,
    list_entries,
    search_entries,
)

router = APIRouter()


class AddEntryRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class PlanRequest(BaseModel):
    product: str = "PUBG Mobile VN"
    period: str
    topic: str
    extra_context: str = ""


@router.post("/entries")
async def create_entry(req: AddEntryRequest):
    entry = add_entry(req.title, req.content, req.tags)
    return entry


@router.get("/entries")
async def get_entries(q: str | None = None, limit: int = 20):
    if q:
        return search_entries(q, limit)
    return list_entries(limit)


@router.delete("/entries/{entry_id}")
async def remove_entry(entry_id: str):
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"deleted": entry_id}


@router.post("/plan")
async def create_plan(req: PlanRequest):
    plan = await generate_social_plan(req.product, req.period, req.topic, req.extra_context)
    return {"plan": plan}
