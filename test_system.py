#!/usr/bin/env python3
"""
Direct testing script for GemFeed system components
"""
import os
import sys
sys.path.append('.')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_database():
    """Test database connectivity"""
    try:
        from app import app, db
        with app.app_context():
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            print("✅ Database: Connected successfully")
            return True
    except Exception as e:
        print(f"❌ Database: {e}")
        return False

def test_news_collection():
    """Test news collection from cybersecurity sources"""
    try:
        from app import app, db
        from models import NewsArticle
        from news_collector import NewsCollector
        
        with app.app_context():
            collector = NewsCollector()
            
            # Test single source
            test_source = {
                'url': 'https://krebsonsecurity.com/feed/',
                'type': 'rss',
                'category': 'security',
                'enabled': True
            }
            
            print("🔍 Testing news collection...")
            count = collector.collect_from_source('krebsonsecurity', test_source)
            
            total_articles = NewsArticle.query.count()
            
            print(f"✅ News Collection: Collected {count} new articles")
            print(f"📰 Total articles in database: {total_articles}")
            return True
            
    except Exception as e:
        print(f"❌ News Collection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_telegram_config():
    """Test Telegram configuration"""
    try:
        from config import Config
        
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        
        if not token:
            print("⚠️  Telegram: Bot token not configured")
            return False
        
        if not chat_id:
            print("⚠️  Telegram: Chat ID not configured")
            return False
            
        print("✅ Telegram: Configuration found")
        
        # Test bot connection
        from telegram_bot import TelegramBot
        bot = TelegramBot()
        if bot.validate_config():
            print("✅ Telegram: Bot connection successful")
            return True
        else:
            print("❌ Telegram: Bot connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Telegram: {e}")
        return False

def main():
    """Run all system tests"""
    print("🚀 Starting GemFeed System Tests\n")
    
    results = []
    
    # Test components
    results.append(("Database", test_database()))
    results.append(("News Collection", test_news_collection()))
    results.append(("Telegram", test_telegram_config()))
    
    # Summary
    print("\n📊 Test Results:")
    print("-" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All systems operational!")
    elif passed > 0:
        print("⚠️  System partially operational - check failed components")
    else:
        print("🚨 System not operational - check configuration")

if __name__ == "__main__":
    main()