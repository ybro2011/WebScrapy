from celery import Celery
import os
import logging
import redis
from redis.exceptions import ConnectionError, TimeoutError
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Log the Redis configuration
logger.info(f"Redis Configuration:")
logger.info(f"  Host: {REDIS_HOST}")
logger.info(f"  Port: {REDIS_PORT}")
logger.info(f"  DB: {REDIS_DB}")
logger.info(f"  Password: {'set' if REDIS_PASSWORD else 'not set'}")

def wait_for_redis():
    """Wait for Redis to become available."""
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Try to connect to Redis directly
            r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                socket_timeout=1,
                socket_connect_timeout=1,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True
            )
            
            # Test the connection
            r.ping()
            logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            time.sleep(retry_delay)
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
            time.sleep(retry_delay)
    
    logger.error("Failed to connect to Redis after maximum retries")
    return False

# Wait for Redis before configuring Celery
if not wait_for_redis():
    raise RuntimeError("Could not connect to Redis")

# Initialize Celery with Redis broker and backend
celery = Celery('webscraper',
                broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
                backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')

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