import atexit
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from news_collector import NewsCollector
from telegram_bot import TelegramBot
from config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class GemFeedScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
        self.news_collector = NewsCollector()
        self.telegram_bot = TelegramBot()
        
        # Add event listeners
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
    def _job_listener(self, event):
        """Listen to job events for monitoring"""
        if event.exception:
            logger.error(f"Job {event.job_id} crashed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")
    
    def start(self):
        """Start the scheduler with all jobs"""
        try:
            logger.info("Initializing GemFeed Scheduler")
            
            # Validate Telegram configuration first
            telegram_valid = self.telegram_bot.validate_config()
            if not telegram_valid:
                logger.warning("Telegram not configured - will collect news but won't send notifications")
            
            # Add jobs
            self._add_news_collection_job()
            self._add_telegram_sender_job()
            self._add_cleanup_job()
            self._add_retry_job()
            
            # Start the scheduler
            self.scheduler.start()
            logger.info("GemFeed Scheduler started successfully")
            
            # Register shutdown handler
            atexit.register(self.shutdown)
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def _add_news_collection_job(self):
        """Add news collection job"""
        self.scheduler.add_job(
            func=self.news_collector.collect_all_sources,
            trigger=IntervalTrigger(minutes=Config.NEWS_COLLECTION_INTERVAL),
            id='news_collection',
            name='Collect Cybersecurity News',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # 5 minutes grace time
        )
        logger.info(f"News collection job scheduled every {Config.NEWS_COLLECTION_INTERVAL} minutes")
    
    def _add_telegram_sender_job(self):
        """Add Telegram sender job"""
        self.scheduler.add_job(
            func=self.telegram_bot.send_pending_articles,
            trigger=IntervalTrigger(minutes=Config.TELEGRAM_SEND_INTERVAL),
            id='telegram_sender',
            name='Send Telegram Messages',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=120  # 2 minutes grace time
        )
        logger.info(f"Telegram sender job scheduled every {Config.TELEGRAM_SEND_INTERVAL} minutes")
    
    def _add_cleanup_job(self):
        """Add cleanup job"""
        # Run cleanup daily at 2 AM UTC
        self.scheduler.add_job(
            func=self.news_collector.cleanup_old_articles,
            trigger=CronTrigger(hour=2, minute=0),
            id='cleanup',
            name='Database Cleanup',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Cleanup job scheduled daily at 2 AM UTC")
    
    def _add_retry_job(self):
        """Add retry job for failed Telegram messages"""
        self.scheduler.add_job(
            func=self.telegram_bot.retry_failed_messages,
            trigger=IntervalTrigger(hours=2),
            id='telegram_retry',
            name='Retry Failed Telegram Messages',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Telegram retry job scheduled every 2 hours")
    
    def run_immediate_collection(self):
        """Run immediate news collection (for testing/manual trigger)"""
        try:
            logger.info("Running immediate news collection")
            count = self.news_collector.collect_all_sources()
            return count
        except Exception as e:
            logger.error(f"Immediate collection failed: {e}")
            return 0
    
    def run_immediate_telegram_send(self):
        """Run immediate Telegram send (for testing/manual trigger)"""
        try:
            logger.info("Running immediate Telegram send")
            count = self.telegram_bot.send_pending_articles()
            return count
        except Exception as e:
            logger.error(f"Immediate Telegram send failed: {e}")
            return 0
    
    def get_job_status(self):
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler shutdown completed")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")

# Global scheduler instance
scheduler_instance = None

def start_scheduler():
    """Initialize and start the global scheduler"""
    global scheduler_instance
    
    if scheduler_instance is None:
        scheduler_instance = GemFeedScheduler()
        scheduler_instance.start()
    
    return scheduler_instance

def get_scheduler():
    """Get the global scheduler instance"""
    return scheduler_instance
