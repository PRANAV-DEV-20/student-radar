from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "student_radar_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",  # All crontab values below are IST.
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    beat_schedule={
        # 1. Scrape / deduplicate opportunities before the morning briefing.
        "crawl-opportunities-5-30-am-ist": {
            "task": "app.workers.tasks.crawl_and_deduplicate_opportunities",
            "schedule": crontab(
                hour=settings.CRAWL_HOUR_IST,
                minute=settings.CRAWL_MINUTE_IST,
            ),
        },
        # 2. Refresh cross-platform signal snapshots before the dashboard loads.
        "refresh-signal-cache-6-00-am-ist": {
            "task": "app.workers.tasks.refresh_signal_cache",
            "schedule": crontab(
                hour=settings.SIGNAL_REFRESH_HOUR_IST,
                minute=settings.SIGNAL_REFRESH_MINUTE_IST,
            ),
        },
        # 3. Daily briefing at 7:00 AM IST.
        "build-daily-briefings-7-00-am-ist": {
            "task": "app.workers.tasks.compile_daily_user_briefings",
            "schedule": crontab(hour=settings.DAILY_BRIEFING_HOUR_IST, minute=0),
        },
        # 4. Weekly "Strongest Pick" briefing every Sunday at 6:00 PM IST.
        "build-weekly-briefings-sunday-6-00-pm-ist": {
            "task": "app.workers.tasks.compile_weekly_user_briefings",
            "schedule": crontab(
                hour=settings.WEEKLY_BRIEFING_HOUR_IST,
                minute=0,
                day_of_week=0,  # Sunday (Celery: 0 = Sunday)
            ),
        },
    },
)
