import logging
from app import app
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        # Start the background scheduler
        start_scheduler()
        logger.info("Starting GemFeed Cybersecurity News Aggregator")
        
        # Start the Flask app
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
