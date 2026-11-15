from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "student_radar_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata", # Scheduled at IST times
    enable_utc=True,
    beat_schedule={
        "crawl-opportunities-5-30-am-ist": {
            "task": "app.workers.tasks.crawl_and_deduplicate_opportunities",
            "schedule": crontab(hour=5, minute=30), # 5:30 AM IST
        },
        "build-daily-briefings-6-30-am-ist": {
            "task": "app.workers.tasks.compile_daily_user_briefings",
            "schedule": crontab(hour=6, minute=30), # 6:30 AM IST
        },
    }
)

