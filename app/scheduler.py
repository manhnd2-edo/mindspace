import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def start_scheduler():
    from app.modules.airtable_monitor import run_daily_check
    from app.modules.sentiment_tracker import run_weekly_sentiment

    # Daily Airtable check at 09:00 ICT (UTC+7 = 02:00 UTC)
    scheduler.add_job(
        run_daily_check,
        CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="airtable_daily_check",
        replace_existing=True,
    )

    # Weekly sentiment report every Monday at 08:00 ICT (01:00 UTC)
    scheduler.add_job(
        run_weekly_sentiment,
        CronTrigger(day_of_week="mon", hour=1, minute=0, timezone="UTC"),
        id="weekly_sentiment",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started: daily Airtable check + weekly sentiment")


def stop_scheduler():
    scheduler.shutdown(wait=False)
