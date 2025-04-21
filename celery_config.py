import os
from celery import Celery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path of the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define Celery data directories
CELERY_DATA_DIR = os.path.join(BASE_DIR, 'celery_data')
QUEUE_DIR = os.path.join(CELERY_DATA_DIR, 'queue')
PROCESSED_DIR = os.path.join(CELERY_DATA_DIR, 'processed')
RESULTS_DIR = os.path.join(CELERY_DATA_DIR, 'results')

# Create directories if they don't exist
os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Initialize Celery app with filesystem broker and backend
celery_app = Celery('tasks',
             broker='filesystem://',
             backend='filesystem://',
             broker_transport_options={
                 'data_folder_in': QUEUE_DIR,
                 'data_folder_out': QUEUE_DIR,
                 'data_folder_processed': PROCESSED_DIR
             },
             result_backend_options={
                 'data_folder': RESULTS_DIR
             })

# Celery configuration
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=30,
    task_time_limit=86400,  # 24 hours
    task_soft_time_limit=82800,  # 23 hours
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=1,
    worker_max_memory_per_child=500000,  # 500MB
    broker_transport='filesystem',
    result_backend='filesystem'
)

# Export the Celery app
celery = celery_app 