import os
import redis
from rq import Worker, Queue, Connection
import sys
# from utils.logger import get_logger

# Initialize logger
# logger = get_logger(__name__)
# logger.info("Worker started")
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Redis connection
redis_conn = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379))
)

if __name__ == '__main__':
    # Start worker
    with Connection(redis_conn):
        worker = Worker(Queue('default'))
        worker.work()
