from celery import Celery
import os

# Initialize Celery
celery = Celery('webscraper',
                broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
                backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=86400,  # 24 hours
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10
) 