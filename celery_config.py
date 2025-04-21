from celery import Celery
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get absolute path of current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create necessary directories with proper permissions
CELERY_DATA_DIR = os.path.join(BASE_DIR, 'celery_data')
QUEUE_DIR = os.path.join(CELERY_DATA_DIR, 'queue')
PROCESSED_DIR = os.path.join(CELERY_DATA_DIR, 'processed')
RESULTS_DIR = os.path.join(CELERY_DATA_DIR, 'results')

# Create directories with proper permissions
for directory in [CELERY_DATA_DIR, QUEUE_DIR, PROCESSED_DIR, RESULTS_DIR]:
    try:
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o777)  # Set full permissions
        logger.info(f"Created/verified directory: {directory}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        raise

# Initialize Celery with filesystem broker and backend
celery = Celery('webscraper',
                broker='filesystem://',
                backend='filesystem://')

# Configure filesystem broker and backend with absolute paths
celery.conf.broker_transport_options = {
    'data_folder_in': QUEUE_DIR,
    'data_folder_out': QUEUE_DIR,
    'data_folder_processed': PROCESSED_DIR
}
celery.conf.result_backend = f'file://{RESULTS_DIR}'

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