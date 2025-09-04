#!/usr/bin/env python3
"""
GemFeed - Streamlined Cybersecurity News Aggregation System
Based on your requirements for reliable RSS-to-Telegram delivery
"""
import os
import sqlite3
import feedparser
import requests
import logging
import time
from datetime import datetime
import threading
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemfeed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Telegram Setup ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8000643209:AAEyUlsLk6azaFr3MliT-p3MH2Em1gzM-zo")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002646603771")

DB_FILE = "gemfeed.db"

# --- Database Setup ---
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # RSS feeds table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            enabled INTEGER DEFAULT 1,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Articles table with Telegram tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            content TEXT,
            feed_id INTEGER,
            published_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_sent INTEGER DEFAULT 0,
            telegram_sent_at TIMESTAMP,
            FOREIGN KEY(feed_id) REFERENCES rss_feeds(id)
        )
    """)
    
    # System status tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            status TEXT NOT NULL,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized successfully")

# --- Feed Management ---
def add_feed(name, url):
    """Add RSS feed to database"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO rss_feeds (name, url) VALUES (?, ?)", (name, url))
        conn.commit()
        logger.info(f"📡 Added feed: {name}")
    except Exception as e:
        logger.error(f"❌ Error adding feed {name}: {e}")
    finally:
        conn.close()

def get_feeds():
    """Get all active RSS feeds"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, name, url FROM rss_feeds WHERE enabled = 1")
    feeds = cur.fetchall()
    conn.close()
    return feeds

# --- Article Management ---
def save_article(title, link, content, feed_id, published_date=None):
    """Save article if new, return True if new article"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        # Check if article already exists
        cur.execute("SELECT id FROM articles WHERE link = ?", (link,))
        if cur.fetchone():
            return False  # Article already exists
        
        # Insert new article
        cur.execute(
            "INSERT INTO articles (title, link, content, feed_id, published_date) VALUES (?, ?, ?, ?, ?)",
            (title, link, content, feed_id, published_date)
        )
        conn.commit()
        return True  # New article added
    except Exception as e:
        logger.error(f"❌ Error saving article '{title}': {e}")
        return False
    finally:
        conn.close()

def get_unsent_articles(limit=5):
    """Get articles that haven't been sent to Telegram"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.title, a.link, a.content, f.name 
        FROM articles a 
        JOIN rss_feeds f ON a.feed_id = f.id 
        WHERE a.telegram_sent = 0 
        ORDER BY a.created_at DESC 
        LIMIT ?
    """, (limit,))
    articles = cur.fetchall()
    conn.close()
    return articles

def mark_article_sent(article_id):
    """Mark article as sent to Telegram"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE articles SET telegram_sent = 1, telegram_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (article_id,)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error marking article as sent: {e}")
    finally:
        conn.close()

# --- Telegram Integration ---
def send_to_telegram(title, content, link, source):
    """Send formatted message to Telegram channel"""
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("❌ Telegram credentials not configured")
        return False
    
    try:
        # Format message with cybersecurity styling
        message = f"""🔒 <b>{title}</b>

📰 <i>Source: {source}</i>
🕒 <i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>

{content[:300]}{'...' if len(content) > 300 else ''}

<a href="{link}">🔗 Read Full Article</a>
"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, data=data, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"✅ Sent to Telegram: {title[:50]}...")
            return True
        else:
            logger.error(f"❌ Telegram API error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")
        return False

# --- RSS Feed Processing ---
def fetch_and_process_feeds():
    """Fetch RSS feeds and process new articles"""
    feeds = get_feeds()
    total_new_articles = 0
    
    logger.info(f"🔍 Checking {len(feeds)} RSS feeds for updates...")
    
    for feed_id, name, url in feeds:
        try:
            logger.info(f"📡 Processing: {name}")
            parsed = feedparser.parse(url)
            
            if not parsed.entries:
                logger.warning(f"⚠️ No entries found in {name}")
                continue
            
            new_count = 0
            for entry in parsed.entries[:10]:  # Process latest 10 entries
                title = entry.get("title", "No title").strip()
                content = entry.get("summary", entry.get("description", "No content")).strip()
                link = entry.get("link", "")
                
                # Get published date if available
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                
                # Save article (only if new)
                if save_article(title, link, content, feed_id, published_date):
                    new_count += 1
                    total_new_articles += 1
            
            logger.info(f"✅ {name}: {new_count} new articles")
            
            # Update feed's last checked timestamp
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("UPDATE rss_feeds SET last_checked = CURRENT_TIMESTAMP WHERE id = ?", (feed_id,))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error processing {name}: {e}")
    
    logger.info(f"📊 Total new articles collected: {total_new_articles}")
    return total_new_articles

def send_pending_articles():
    """Send unsent articles to Telegram"""
    articles = get_unsent_articles(5)  # Send up to 5 articles at a time
    
    if not articles:
        logger.info("📱 No pending articles to send")
        return 0
    
    sent_count = 0
    logger.info(f"📱 Sending {len(articles)} articles to Telegram...")
    
    for article_id, title, link, content, source in articles:
        if send_to_telegram(title, content, link, source):
            mark_article_sent(article_id)
            sent_count += 1
            time.sleep(2)  # Rate limiting
        else:
            break  # Stop on first failure to avoid spam
    
    logger.info(f"✅ Successfully sent {sent_count} articles to Telegram")
    return sent_count

# --- System Status ---
def update_system_status(component, status, message=""):
    """Update system component status"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR REPLACE INTO system_status (component, status, message, last_update)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (component, status, message))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error updating status: {e}")
    finally:
        conn.close()

def get_system_stats():
    """Get system statistics"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Get counts
    cur.execute("SELECT COUNT(*) FROM articles")
    total_articles = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM articles WHERE telegram_sent = 1")
    sent_articles = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM articles WHERE telegram_sent = 0")
    pending_articles = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM rss_feeds WHERE enabled = 1")
    active_feeds = cur.fetchone()[0]
    
    conn.close()
    
    return {
        'total_articles': total_articles,
        'sent_articles': sent_articles,
        'pending_articles': pending_articles,
        'active_feeds': active_feeds
    }

# --- Automated Workflow ---
def run_collection_cycle():
    """Run complete news collection and delivery cycle"""
    logger.info("🚀 Starting collection cycle...")
    
    try:
        # Update status
        update_system_status("collector", "running", "Collecting news from RSS feeds")
        
        # Collect new articles
        new_articles = fetch_and_process_feeds()
        
        # Send to Telegram
        sent_articles = send_pending_articles()
        
        # Update final status
        stats = get_system_stats()
        update_system_status("collector", "active", 
                           f"Collected: {new_articles}, Sent: {sent_articles}, Pending: {stats['pending_articles']}")
        
        logger.info("✅ Collection cycle completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Collection cycle failed: {e}")
        update_system_status("collector", "error", str(e))

def setup_scheduler():
    """Set up automated scheduling"""
    # Schedule news collection every 15 minutes
    schedule.every(15).minutes.do(run_collection_cycle)
    
    logger.info("⏰ Scheduler configured - collecting every 15 minutes")
    
    # Run scheduler in separate thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# --- Setup Functions ---
def setup_cybersecurity_feeds():
    """Add default cybersecurity news feeds"""
    feeds = [
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
        ("Dark Reading", "https://www.darkreading.com/rss.xml"),
        ("CISA Advisories", "https://www.cisa.gov/cybersecurity-advisories.xml"),
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
        ("Bleeping Computer", "https://www.bleepingcomputer.com/feed/"),
        ("Security Week", "https://www.securityweek.com/feed/"),
        ("Threatpost", "https://threatpost.com/feed/")
    ]
    
    logger.info("📡 Setting up cybersecurity news feeds...")
    for name, url in feeds:
        add_feed(name, url)

def test_telegram_connection():
    """Test Telegram bot connection"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()['result']
            logger.info(f"✅ Telegram bot connected: @{bot_info['username']}")
            
            # Send test message
            test_msg = "🔒 GemFeed Cybersecurity News System\n✅ System initialized and ready\n🚀 Automated news delivery active"
            if send_to_telegram("System Status", test_msg, "", "GemFeed System"):
                logger.info("✅ Test message sent successfully")
                return True
        
        logger.error("❌ Telegram connection test failed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Telegram test error: {e}")
        return False

# --- Main Application ---
def main():
    """Main application entry point"""
    logger.info("🚀 GemFeed Cybersecurity News System Starting...")
    
    # Initialize system
    init_db()
    setup_cybersecurity_feeds()
    
    # Test Telegram
    if test_telegram_connection():
        update_system_status("telegram", "active", "Bot connected and tested")
    else:
        update_system_status("telegram", "error", "Connection failed")
    
    # Run initial collection
    logger.info("🔄 Running initial news collection...")
    run_collection_cycle()
    
    # Set up automated scheduling
    setup_scheduler()
    
    # Display system status
    stats = get_system_stats()
    logger.info("📊 System Status:")
    logger.info(f"   Active Feeds: {stats['active_feeds']}")
    logger.info(f"   Total Articles: {stats['total_articles']}")
    logger.info(f"   Sent to Telegram: {stats['sent_articles']}")
    logger.info(f"   Pending Delivery: {stats['pending_articles']}")
    
    update_system_status("system", "active", "All components operational")
    logger.info("✅ GemFeed system is fully operational!")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 System shutdown requested")
        update_system_status("system", "stopped", "Manual shutdown")

if __name__ == "__main__":
    main()