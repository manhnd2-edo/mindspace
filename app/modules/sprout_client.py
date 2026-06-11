"""Thin async wrapper around the Sprout Social Reporting API v1."""
import logging
from datetime import date, timezone, datetime
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
BASE_URL = "https://api.sproutsocial.com/v1"


def _iso_start(d: date) -> str:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def _iso_end(d: date) -> str:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def _profile_params(customer_id: str) -> dict:
    return {"filtering[customer_profile_ids][]": customer_id}


class SproutClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.sprout_token}",
            "Content-Type": "application/json",
        }
        self.customer_id = settings.sprout_customer_id

    async def get_profile_analytics(
        self,
        start_date: date,
        end_date: date,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch aggregated profile-level metrics for the date range."""
        if fields is None:
            fields = [
                "lifetime_snapshot.followers_count",
                "net_follower_growth",
                "impressions",
                "engagements",
                "reactions",
                "comments",
                "shares",
                "link_clicks",
                "video_views",
            ]
        body = {
            "filters": [
                {
                    "field": "customer_profile_id",
                    "operator": "IN",
                    "value": [int(self.customer_id)],
                },
                {
                    "field": "reporting_period",
                    "operator": "BETWEEN",
                    "value": {
                        "start_time": _iso_start(start_date),
                        "end_time": _iso_end(end_date),
                    },
                },
            ],
            "metrics": fields,
        }
        return await self._post(f"/{self.customer_id}/analytics/profiles", body)

    async def get_post_analytics(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Fetch per-post metrics."""
        body = {
            "metrics": ["impressions", "engagements", "reactions", "comments", "shares", "link_clicks"],
            "start_time": _iso_start(start_date),
            "end_time": _iso_end(end_date),
            "page": {"count": 100},
        }
        return await self._post(
            f"/{self.customer_id}/analytics/posts", body, _profile_params(self.customer_id)
        )

    async def get_inbox_messages(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Fetch inbox/mention messages for sentiment analysis."""
        body = {
            "fields": ["message_id", "text", "sentiment", "created_time", "sender_id", "network_type"],
            "start_time": _iso_start(start_date),
            "end_time": _iso_end(end_date),
            "page": {"count": 200},
        }
        params = _profile_params(self.customer_id)
        params["filtering[message_types][]"] = "MENTION,COMMENT,REPLY"
        return await self._post(f"/{self.customer_id}/messages", body, params)

    async def _post(self, path: str, body: dict, params: dict | None = None) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, json=body, params=params, headers=self.headers)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Sprout API error %s: %s", e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("Sprout request failed: %s", e)
            raise


sprout = SproutClient()
