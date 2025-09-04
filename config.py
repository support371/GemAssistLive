import os
import logging

logger = logging.getLogger(__name__)

class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8000643209:AAEyUlsLk6azaFr3MliT-p3MH2Em1gzM-zo")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002646603771")
    
    # News Sources Configuration
    NEWS_SOURCES = {
        'threatpost': {
            'url': 'https://threatpost.com/feed/',
            'type': 'rss',
            'category': 'threats',
            'enabled': True
        },
        'krebsonsecurity': {
            'url': 'https://krebsonsecurity.com/feed/',
            'type': 'rss',
            'category': 'security',
            'enabled': True
        },
        'darkreading': {
            'url': 'https://www.darkreading.com/rss.xml',
            'type': 'rss',
            'category': 'security',
            'enabled': True
        },
        'bleepingcomputer': {
            'url': 'https://www.bleepingcomputer.com/feed/',
            'type': 'rss',
            'category': 'cybersecurity',
            'enabled': True
        },
        'securityweek': {
            'url': 'https://www.securityweek.com/feed',
            'type': 'rss',
            'category': 'security',
            'enabled': True
        },
        'thehackernews': {
            'url': 'https://feeds.feedburner.com/TheHackersNews',
            'type': 'rss',
            'category': 'cybersecurity',
            'enabled': True
        }
    }
    
    # Rate Limiting Configuration
    MAX_REQUESTS_PER_MINUTE = 30
    MAX_ARTICLES_PER_BATCH = 50
    MAX_TELEGRAM_RETRIES = 3
    RETRY_DELAY_SECONDS = 60
    
    # Collection Intervals (in minutes)
    NEWS_COLLECTION_INTERVAL = 15
    TELEGRAM_SEND_INTERVAL = 5
    CLEANUP_INTERVAL = 1440  # 24 hours
    
    # Memory Management
    MAX_ARTICLES_RETENTION_DAYS = 30
    MAX_LOG_FILE_SIZE_MB = 50
    
    # Timeout Configuration
    REQUEST_TIMEOUT = 30
    
    @classmethod
    def validate_config(cls):
        """Validate essential configuration"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == "":
            errors.append("TELEGRAM_BOT_TOKEN environment variable is required")
            
        if not cls.TELEGRAM_CHAT_ID or cls.TELEGRAM_CHAT_ID == "":
            errors.append("TELEGRAM_CHAT_ID environment variable is required")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Configuration validated successfully")
        return True
