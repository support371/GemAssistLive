#!/usr/bin/env python3
"""
Direct test of cybersecurity news collection and Telegram delivery
"""
import sys
sys.path.append('.')

from app import app, db
from models import NewsArticle
from news_collector import NewsCollector
from telegram_bot import TelegramBot
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_news_collection():
    """Test news collection"""
    with app.app_context():
        collector = NewsCollector()
        total_collected = 0
        
        logger.info("🔍 Starting cybersecurity news collection...")
        
        for source_name, source_config in Config.NEWS_SOURCES.items():
            if not source_config.get('enabled', True):
                continue
                
            try:
                count = collector.collect_from_source(source_name, source_config)
                total_collected += count
                logger.info(f"✅ {source_name}: {count} new articles")
            except Exception as e:
                logger.error(f"❌ {source_name}: {e}")
        
        total_articles = NewsArticle.query.count()
        unsent_articles = NewsArticle.query.filter_by(telegram_sent=False).count()
        
        logger.info(f"📊 Collection Summary:")
        logger.info(f"   - New articles collected: {total_collected}")
        logger.info(f"   - Total articles in database: {total_articles}")
        logger.info(f"   - Articles pending Telegram: {unsent_articles}")
        
        return total_collected

def test_telegram_delivery():
    """Test Telegram message delivery"""
    with app.app_context():
        bot = TelegramBot()
        
        # Validate configuration first
        if not bot.validate_config():
            logger.error("❌ Telegram configuration invalid")
            return 0
        
        # Get unsent articles
        unsent_articles = NewsArticle.query.filter_by(telegram_sent=False).limit(3).all()
        
        if not unsent_articles:
            logger.info("📱 No articles to send to Telegram")
            return 0
        
        logger.info(f"📱 Sending {len(unsent_articles)} articles to Telegram...")
        
        sent_count = 0
        for article in unsent_articles:
            try:
                # Format message
                message = f"""
🔒 <b>{article.title}</b>

📰 <i>{article.source}</i>
🕒 {article.published_at.strftime('%Y-%m-%d %H:%M')}

{article.description[:200]}...

<a href="{article.url}">Read Full Article</a>
"""
                
                if bot.send_message(message):
                    article.telegram_sent = True
                    article.telegram_sent_at = db.func.current_timestamp()
                    sent_count += 1
                    logger.info(f"✅ Sent: {article.title[:50]}...")
                else:
                    logger.error(f"❌ Failed to send: {article.title[:50]}...")
                    
            except Exception as e:
                logger.error(f"❌ Error sending article: {e}")
        
        # Commit changes
        try:
            db.session.commit()
            logger.info(f"📱 Successfully sent {sent_count} articles to Telegram")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error: {e}")
        
        return sent_count

def main():
    """Run complete test workflow"""
    logger.info("🚀 Starting GemFeed Complete Workflow Test")
    logger.info(f"🔗 Target Channel: {Config.TELEGRAM_CHAT_ID}")
    logger.info("-" * 60)
    
    # Test 1: News Collection
    collected = test_news_collection()
    
    logger.info("-" * 60)
    
    # Test 2: Telegram Delivery
    sent = test_telegram_delivery()
    
    logger.info("-" * 60)
    logger.info("🎯 Workflow Test Summary:")
    logger.info(f"   ✅ Articles collected: {collected}")
    logger.info(f"   ✅ Messages sent: {sent}")
    
    if collected > 0 and sent > 0:
        logger.info("🎉 Complete workflow successful!")
    elif collected > 0:
        logger.info("⚠️  Collection works, check Telegram configuration")
    else:
        logger.info("❌ No articles collected - check RSS feeds")

if __name__ == "__main__":
    main()