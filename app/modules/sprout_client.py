"""Mock Sprout Social client — returns realistic PUBG Mobile VN sample data.

Drop-in replacement for the real Sprout client. Swap back by pointing
_post() at the real API and adding Bearer auth when credentials are available.
"""
import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class SproutClient:
    def __init__(self):
        self.customer_id = "2416203"

    async def get_profile_analytics(
        self,
        start_date: date,
        end_date: date,
        metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        days = (end_date - start_date).days + 1
        daily = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            daily.append({
                "dimensions": {"customer_profile_id": int(self.customer_id)},
                "date": str(d),
                "metrics": {
                    "lifetime_snapshot.followers_count": 1_280_000 + i * 420,
                    "net_follower_growth": 380 + (i % 3) * 60,
                    "impressions": 95_000 + (i % 7) * 8_500,
                    "engagements": 4_200 + (i % 5) * 380,
                    "reactions": 3_100 + (i % 5) * 280,
                    "comments_count": 620 + (i % 4) * 55,
                    "shares_count": 480 + (i % 4) * 40,
                    "video_views": 28_000 + (i % 6) * 3_200,
                },
            })
        logger.info("[MOCK] get_profile_analytics %s → %s (%d days)", start_date, end_date, days)
        return {
            "data": daily,
            "paging": {"total_count": days, "current_page": 1, "total_pages": 1},
        }

    async def get_post_analytics(self, start_date: date, end_date: date) -> dict[str, Any]:
        sample_posts = [
            {
                "guid": "fb:1001",
                "created_time": str(start_date),
                "network": "FACEBOOK",
                "post_type": "FACEBOOK_POST",
                "text": "🔥 PUBG MOBILE Season 20 chính thức ra mắt! Khám phá bản đồ mới Rondo ngay hôm nay.",
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1001",
                "metrics": {
                    "lifetime.impressions": 142_000,
                    "lifetime.reactions": 8_700,
                    "lifetime.likes": 7_200,
                    "lifetime.comments": 1_340,
                    "lifetime.shares": 980,
                    "lifetime.engagements": 10_040,
                    "lifetime.video_views": 0,
                    "lifetime.clicks": 2_300,
                },
            },
            {
                "guid": "fb:1002",
                "created_time": str(start_date + timedelta(days=1)),
                "network": "FACEBOOK",
                "post_type": "FACEBOOK_REEL",
                "text": "Highlight kèo đỉnh của tuần — ai nhận ra map này? 👀 #PUBGMOBILE #Season20",
                "perma_link": "https://facebook.com/pubgmobilevn/reels/1002",
                "metrics": {
                    "lifetime.impressions": 210_000,
                    "lifetime.reactions": 14_200,
                    "lifetime.likes": 12_500,
                    "lifetime.comments": 2_100,
                    "lifetime.shares": 3_400,
                    "lifetime.engagements": 16_300,
                    "lifetime.video_views": 185_000,
                    "lifetime.clicks": 4_700,
                },
            },
            {
                "guid": "fb:1003",
                "created_time": str(start_date + timedelta(days=2)),
                "network": "FACEBOOK",
                "post_type": "FACEBOOK_POST",
                "text": "Sự kiện Chicken Dinner Carnival tuần này — đăng ký ngay để nhận skin exclusive!",
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1003",
                "metrics": {
                    "lifetime.impressions": 88_000,
                    "lifetime.reactions": 4_300,
                    "lifetime.likes": 3_800,
                    "lifetime.comments": 760,
                    "lifetime.shares": 420,
                    "lifetime.engagements": 5_060,
                    "lifetime.video_views": 0,
                    "lifetime.clicks": 6_200,
                },
            },
            {
                "guid": "fb:1004",
                "created_time": str(start_date + timedelta(days=3)),
                "network": "FACEBOOK",
                "post_type": "FACEBOOK_POST",
                "text": "Update patch 3.2 — cân bằng vũ khí và fix lỗi. Chi tiết trong bình luận 👇",
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1004",
                "metrics": {
                    "lifetime.impressions": 76_000,
                    "lifetime.reactions": 2_900,
                    "lifetime.likes": 2_400,
                    "lifetime.comments": 1_820,
                    "lifetime.shares": 310,
                    "lifetime.engagements": 4_720,
                    "lifetime.video_views": 0,
                    "lifetime.clicks": 3_900,
                },
            },
        ]
        logger.info("[MOCK] get_post_analytics %s → %s", start_date, end_date)
        return {
            "data": sample_posts,
            "paging": {"total_count": len(sample_posts), "current_page": 1, "total_pages": 1},
        }

    async def get_inbox_messages(self, start_date: date, end_date: date) -> dict[str, Any]:
        messages = [
            {
                "guid": "msg:2001",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date),
                "text": "Game hay quá, season này map mới đỉnh lắm! Mong thêm event nữa nha team.",
                "from": {"name": "Nguyễn Văn A"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1001?comment=2001",
            },
            {
                "guid": "msg:2002",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date + timedelta(days=1)),
                "text": "Server lag quá, chiều tối hay bị disconnect. Fix được không team ơi?",
                "from": {"name": "Trần Thị B"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1001?comment=2002",
            },
            {
                "guid": "msg:2003",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date + timedelta(days=1)),
                "text": "Skin mới đẹp vãi, nhưng giá hơi cao. Có event miễn phí không team?",
                "from": {"name": "Lê Minh C"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1002?comment=2003",
            },
            {
                "guid": "msg:2004",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date + timedelta(days=2)),
                "text": "Patch mới nerf M416 hơi nhiều rồi, chơi không còn vui nữa 😢",
                "from": {"name": "Phạm Quốc D"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1004?comment=2004",
            },
            {
                "guid": "msg:2005",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date + timedelta(days=3)),
                "text": "Chicken dinner rồi anh em ơi!!! PUBG VN số 1 luôn 🐔🔥",
                "from": {"name": "Hoàng Thế E"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1003?comment=2005",
            },
            {
                "guid": "msg:2006",
                "network": "FACEBOOK",
                "post_type": "FBCR_COMMENT",
                "created_time": str(start_date + timedelta(days=4)),
                "text": "Hack cheat nhiều quá, report mãi không thấy xử lý. Team làm ăn kiểu gì?",
                "from": {"name": "Vũ Thanh F"},
                "perma_link": "https://facebook.com/pubgmobilevn/posts/1004?comment=2006",
            },
        ]
        logger.info("[MOCK] get_inbox_messages %s → %s (%d msgs)", start_date, end_date, len(messages))
        return {
            "data": messages,
            "paging": {"next_cursor": None},
        }


sprout = SproutClient()
