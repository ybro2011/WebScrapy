from celery import Celery
import os

# Create necessary directories
os.makedirs('celery_data', exist_ok=True)

# Initialize Celery with filesystem broker and backend
celery = Celery('webscraper',
                broker='filesystem://',
                backend='filesystem://')

# Configure filesystem broker and backend
celery.conf.broker_transport_options = {
    'data_folder_in': 'celery_data/queue',
    'data_folder_out': 'celery_data/queue',
    'data_folder_processed': 'celery_data/processed'
}
celery.conf.result_backend = 'file:///celery_data/results'

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
    broker_use_ssl=False
) 