#!/usr/bin/env python3
"""
Simple runner for GemFeed system - for manual testing and single runs
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemfeed_simple import (
    init_db, setup_cybersecurity_feeds, test_telegram_connection,
    run_collection_cycle, get_system_stats
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quick_run():
    """Quick test run of the system"""
    logger.info("🚀 GemFeed Quick Test Run")
    
    # Initialize
    init_db()
    setup_cybersecurity_feeds()
    
    # Test Telegram
    logger.info("📱 Testing Telegram connection...")
    telegram_ok = test_telegram_connection()
    
    # Collect and send news
    logger.info("📰 Running news collection cycle...")
    run_collection_cycle()
    
    # Show stats
    stats = get_system_stats()
    logger.info("\n📊 Final Statistics:")
    logger.info(f"   📡 Active Feeds: {stats['active_feeds']}")
    logger.info(f"   📰 Total Articles: {stats['total_articles']}")
    logger.info(f"   ✅ Sent to Telegram: {stats['sent_articles']}")
    logger.info(f"   ⏳ Pending: {stats['pending_articles']}")
    
    if telegram_ok and stats['sent_articles'] > 0:
        logger.info("🎉 System working perfectly!")
    elif stats['total_articles'] > 0:
        logger.info("⚠️ System collecting news but check Telegram")
    else:
        logger.info("❌ System needs troubleshooting")

if __name__ == "__main__":
    quick_run()