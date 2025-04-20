from celery import Celery
import os

# Get Redis connection details from environment
redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = os.environ.get('REDIS_PORT', '6379')
redis_password = os.environ.get('REDIS_PASSWORD', '')
redis_db = os.environ.get('REDIS_DB', '0')

# Construct Redis URL
redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"

# Initialize Celery
celery = Celery('webscraper',
                broker=redis_url,
                backend=redis_url)

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
    broker_connection_max_retries=20,
    broker_connection_timeout=30,
    broker_pool_limit=10,
    broker_heartbeat=10,
    broker_use_ssl=False,
    redis_socket_timeout=30,
    redis_socket_connect_timeout=30,
    redis_retry_on_timeout=True,
    redis_max_connections=10
) 