#!/usr/bin/env python3
"""
GEM Newsletter Automation System
Connects Newsletter content to Telegram with professional formatting
Supports: Logo, Title, Summary, Full Content, Image, Video
"""
import os
import sqlite3
import requests
import logging
from datetime import datetime
import time
import threading
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('newsletter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Telegram Setup ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# GEM Brand Configuration
GEM_LOGO_URL = os.environ.get("GEM_LOGO_URL", "")
BRAND_NAME = "GEM ASSIST"

def validate_telegram_config():
    """Validate that Telegram credentials are configured"""
    if not BOT_TOKEN:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not configured - Telegram sending disabled")
        return False
    if not CHAT_ID:
        logger.warning("⚠️ TELEGRAM_CHAT_ID not configured - Telegram sending disabled")
        return False
    return True

DB_FILE = "newsletter.db"

# --- Database Setup ---
def init_db():
    """Initialize SQLite database with newsletter content tables"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Newsletter content table with all required fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subheading TEXT,
            summary TEXT,
            full_content TEXT,
            image_url TEXT,
            video_url TEXT,
            logo_url TEXT,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_sent INTEGER DEFAULT 0,
            telegram_sent_at TIMESTAMP,
            telegram_message_id INTEGER,
            is_published INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual'
        )
    """)
    
    # Telegram message tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            message_id INTEGER,
            chat_id TEXT,
            media_type TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'sent',
            error_message TEXT,
            FOREIGN KEY(content_id) REFERENCES newsletter_content(id)
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
    logger.info("✅ Newsletter database initialized")

# --- Content Management ---
def add_content(title, summary=None, full_content=None, subheading=None, 
                image_url=None, video_url=None, logo_url=None, category='general', source='manual'):
    """Add new newsletter content to the database"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO newsletter_content 
            (title, subheading, summary, full_content, image_url, video_url, logo_url, category, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, subheading, summary, full_content, image_url, video_url, logo_url, category, source))
        conn.commit()
        content_id = cur.lastrowid
        logger.info(f"📝 Added content: {title[:50]}... (ID: {content_id})")
        return content_id
    except Exception as e:
        logger.error(f"❌ Error adding content: {e}")
        return None
    finally:
        conn.close()

def get_unsent_content(limit=5):
    """Get content that hasn't been sent to Telegram"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, subheading, summary, full_content, image_url, video_url, logo_url, category
        FROM newsletter_content 
        WHERE telegram_sent = 0 AND is_published = 1
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    content = cur.fetchall()
    conn.close()
    return content

def mark_content_sent(content_id, message_id=None):
    """Mark content as sent to Telegram"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE newsletter_content 
            SET telegram_sent = 1, telegram_sent_at = CURRENT_TIMESTAMP, telegram_message_id = ?
            WHERE id = ?
        """, (message_id, content_id))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error marking content as sent: {e}")
    finally:
        conn.close()

def get_all_content(limit=50):
    """Get all newsletter content"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, subheading, summary, full_content, image_url, video_url, logo_url, 
               category, created_at, telegram_sent, telegram_sent_at
        FROM newsletter_content 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    content = cur.fetchall()
    conn.close()
    return content

# --- Telegram Professional Formatter ---
class TelegramFormatter:
    """Professional Telegram message formatter with GEM branding"""
    
    def __init__(self):
        if not validate_telegram_config():
            self.configured = False
            self.bot_token = None
            self.chat_id = None
            self.api_base = None
        else:
            self.configured = True
            self.bot_token = BOT_TOKEN
            self.chat_id = CHAT_ID
            self.api_base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    def send_logo_first(self, logo_url):
        """Send logo as the first message in a content series"""
        if not self.configured or not logo_url:
            return None
        
        try:
            url = f"{self.api_base}/sendPhoto"
            data = {
                "chat_id": self.chat_id,
                "photo": logo_url,
                "caption": f"🔒 <b>{BRAND_NAME}</b>",
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=15)
            if response.status_code == 200:
                return response.json().get('result', {}).get('message_id')
            return None
        except Exception as e:
            logger.warning(f"⚠️ Could not send logo: {e}")
            return None
    
    def format_message(self, title, subheading=None, summary=None, full_content=None, 
                       has_video=False, has_image=False, logo_url=None):
        """Format message with GEM branding structure"""
        
        # Build the message structure
        parts = []
        
        # Header with branding (include logo indicator if available)
        if logo_url:
            parts.append(f"🏢 <b>{BRAND_NAME}</b>")
        else:
            parts.append(f"🔒 <b>{BRAND_NAME}</b>")
        parts.append("")
        
        # Title in caps style
        parts.append(f"📰 <b>{title.upper()}</b>")
        
        # Subheading if available
        if subheading:
            parts.append(f"<i>{subheading}</i>")
        
        parts.append("")
        
        # Summary section
        if summary:
            parts.append("📋 <b>SUMMARY:</b>")
            parts.append(summary[:500])
            parts.append("")
        
        # Full content section (truncated for Telegram limits)
        if full_content:
            # Telegram message limit is 4096 characters
            content_preview = full_content[:1500]
            if len(full_content) > 1500:
                content_preview += "..."
            
            parts.append("📄 <b>FULL CONTENT:</b>")
            parts.append(content_preview)
            parts.append("")
        
        # Footer
        parts.append("━━━━━━━━━━━━━━━━━")
        parts.append(f"📱 <b>@CyberWealthSecure</b>")
        parts.append(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(parts)
    
    def send_with_video(self, content_id, title, subheading, summary, full_content, video_url, logo_url=None):
        """Send content with video as main media"""
        try:
            # Format the caption
            caption = self.format_message(title, subheading, summary, full_content, has_video=True)
            
            # Truncate caption for Telegram video limit (1024 chars)
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
            
            # Send video with caption
            url = f"{self.api_base}/sendVideo"
            data = {
                "chat_id": self.chat_id,
                "video": video_url,
                "caption": caption,
                "parse_mode": "HTML",
                "supports_streaming": True
            }
            
            response = requests.post(url, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('result', {}).get('message_id')
                logger.info(f"✅ Video sent: {title[:50]}...")
                return message_id
            else:
                # Fallback: send as text with video link
                logger.warning(f"⚠️ Video upload failed, sending as link")
                return self.send_text_with_media_link(content_id, title, subheading, summary, full_content, video_url, "video")
                
        except Exception as e:
            logger.error(f"❌ Error sending video: {e}")
            return None
    
    def send_with_image(self, content_id, title, subheading, summary, full_content, image_url, logo_url=None):
        """Send content with image as main media"""
        try:
            # Format the caption
            caption = self.format_message(title, subheading, summary, full_content, has_image=True)
            
            # Truncate caption for Telegram photo limit (1024 chars)
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
            
            # Send photo with caption
            url = f"{self.api_base}/sendPhoto"
            data = {
                "chat_id": self.chat_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('result', {}).get('message_id')
                logger.info(f"✅ Image sent: {title[:50]}...")
                return message_id
            else:
                # Fallback: send as text with image link
                logger.warning(f"⚠️ Image upload failed, sending as link")
                return self.send_text_with_media_link(content_id, title, subheading, summary, full_content, image_url, "image")
                
        except Exception as e:
            logger.error(f"❌ Error sending image: {e}")
            return None
    
    def send_text_only(self, content_id, title, subheading, summary, full_content, logo_url=None):
        """Send text-only content"""
        try:
            # Format the full message
            message = self.format_message(title, subheading, summary, full_content)
            
            # Telegram text limit is 4096 characters
            if len(message) > 4096:
                message = message[:4090] + "..."
            
            url = f"{self.api_base}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, data=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('result', {}).get('message_id')
                logger.info(f"✅ Text sent: {title[:50]}...")
                return message_id
            else:
                logger.error(f"❌ Telegram error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending text: {e}")
            return None
    
    def send_text_with_media_link(self, content_id, title, subheading, summary, full_content, media_url, media_type):
        """Send text with embedded media link (fallback)"""
        try:
            # Add media link to message
            media_label = "🎬 Video" if media_type == "video" else "🖼️ Image"
            
            message = self.format_message(title, subheading, summary, full_content)
            message += f"\n\n{media_label}: {media_url}"
            
            if len(message) > 4096:
                message = message[:4090] + "..."
            
            url = f"{self.api_base}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, data=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result', {}).get('message_id')
            return None
                
        except Exception as e:
            logger.error(f"❌ Error sending with media link: {e}")
            return None
    
    def send_content(self, content_id, title, subheading, summary, full_content, image_url, video_url, logo_url):
        """
        Smart content sender - chooses best method based on available media
        Priority: Video > Image > Text-only
        Sends logo first if available for brand identity
        """
        if not self.configured:
            logger.error("❌ Telegram not configured - cannot send content")
            return None
            
        message_id = None
        
        # Send logo first if available (brand identity)
        effective_logo = logo_url or GEM_LOGO_URL
        if effective_logo:
            logo_msg_id = self.send_logo_first(effective_logo)
            if logo_msg_id:
                logger.info(f"🏢 Logo sent for: {title[:40]}...")
                time.sleep(1)  # Brief pause between logo and content
        
        if video_url:
            # Priority 1: Send with video
            logger.info(f"📹 Sending with video: {title[:40]}...")
            message_id = self.send_with_video(content_id, title, subheading, summary, full_content, video_url, logo_url)
        elif image_url:
            # Priority 2: Send with image
            logger.info(f"🖼️ Sending with image: {title[:40]}...")
            message_id = self.send_with_image(content_id, title, subheading, summary, full_content, image_url, logo_url)
        else:
            # Priority 3: Text only
            logger.info(f"📝 Sending text only: {title[:40]}...")
            message_id = self.send_text_only(content_id, title, subheading, summary, full_content, logo_url)
        
        return message_id

# --- Workflow Functions ---
def send_pending_content():
    """Send all pending newsletter content to Telegram"""
    if not validate_telegram_config():
        logger.warning("⚠️ Telegram not configured - skipping content delivery")
        return 0
        
    formatter = TelegramFormatter()
    if not formatter.configured:
        logger.warning("⚠️ Telegram formatter not initialized - skipping content delivery")
        return 0
        
    content_list = get_unsent_content(5)  # Process up to 5 at a time
    
    if not content_list:
        logger.info("📱 No pending content to send")
        return 0
    
    sent_count = 0
    logger.info(f"📱 Sending {len(content_list)} items to Telegram...")
    
    for item in content_list:
        content_id, title, subheading, summary, full_content, image_url, video_url, logo_url, category = item
        
        message_id = formatter.send_content(
            content_id, title, subheading, summary, full_content, 
            image_url, video_url, logo_url
        )
        
        if message_id:
            mark_content_sent(content_id, message_id)
            sent_count += 1
            time.sleep(3)  # Rate limiting between messages
        else:
            logger.error(f"❌ Failed to send: {title[:50]}")
            break  # Stop on first failure
    
    logger.info(f"✅ Successfully sent {sent_count} items to Telegram")
    return sent_count

def get_system_stats():
    """Get system statistics"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM newsletter_content")
    total_content = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM newsletter_content WHERE telegram_sent = 1")
    sent_content = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM newsletter_content WHERE telegram_sent = 0 AND is_published = 1")
    pending_content = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM newsletter_content WHERE video_url IS NOT NULL AND video_url != ''")
    with_video = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM newsletter_content WHERE image_url IS NOT NULL AND image_url != ''")
    with_image = cur.fetchone()[0]
    
    conn.close()
    
    return {
        'total_content': total_content,
        'sent_content': sent_content,
        'pending_content': pending_content,
        'with_video': with_video,
        'with_image': with_image
    }

def test_telegram_connection():
    """Test Telegram bot connection"""
    if not validate_telegram_config():
        return False
        
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()['result']
            logger.info(f"✅ Telegram bot connected: @{bot_info['username']}")
            return True
        logger.error(f"❌ Telegram bot validation failed: {response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Telegram connection error: {e}")
        return False

def setup_scheduler():
    """Set up automated content delivery schedule"""
    schedule.every(5).minutes.do(send_pending_content)
    logger.info("⏰ Scheduler configured - checking for content every 5 minutes")
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# --- Sample Content for Testing ---
def add_sample_content():
    """Add sample content for testing"""
    samples = [
        {
            'title': 'Critical Zero-Day Vulnerability Discovered in Popular Software',
            'subheading': 'Security researchers urge immediate patching',
            'summary': 'A critical zero-day vulnerability has been discovered affecting millions of users worldwide. The flaw allows remote code execution without user interaction.',
            'full_content': 'Security researchers at GEM Assist have uncovered a critical zero-day vulnerability in widely-used software that could allow attackers to execute arbitrary code remotely. The vulnerability, tracked as CVE-2024-XXXX, affects versions 2.0 through 4.5 of the software.\n\nOrganizations are urged to apply patches immediately or implement recommended mitigations. The vulnerability has a CVSS score of 9.8, indicating critical severity.',
            'image_url': 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800',
            'video_url': None,
            'category': 'vulnerability'
        },
        {
            'title': 'New Ransomware Campaign Targets Healthcare Sector',
            'subheading': 'Hospitals and clinics across multiple regions affected',
            'summary': 'A sophisticated ransomware operation is targeting healthcare organizations with a new variant that encrypts medical records and disrupts critical services.',
            'full_content': 'Healthcare organizations worldwide are being targeted by a new ransomware campaign that specifically exploits vulnerabilities in medical record systems. The attackers are demanding cryptocurrency payments and threatening to release patient data.\n\nGEM Assist recommends implementing network segmentation, regular backups, and employee security training to mitigate this threat.',
            'image_url': 'https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=800',
            'video_url': None,
            'category': 'ransomware'
        },
        {
            'title': 'State-Sponsored Hackers Deploy New Backdoor Malware',
            'subheading': 'Advanced persistent threat group linked to nation-state',
            'summary': 'Intelligence agencies have identified a new backdoor malware being deployed by state-sponsored hackers targeting government and defense contractors.',
            'full_content': 'A sophisticated state-sponsored hacking group has been observed deploying a previously unknown backdoor malware in attacks against government agencies and defense contractors. The malware, dubbed "ShadowGate," establishes persistent access and exfiltrates sensitive data.\n\nThe attack chain begins with spear-phishing emails containing malicious documents. Organizations should review their email security policies and implement advanced threat detection.',
            'image_url': None,
            'video_url': None,
            'category': 'apt'
        }
    ]
    
    for sample in samples:
        add_content(**sample)
    
    logger.info(f"📝 Added {len(samples)} sample content items")

# --- Main Application ---
def main():
    """Main application entry point"""
    logger.info("🚀 GEM Newsletter Automation System Starting...")
    
    # Initialize database
    init_db()
    
    # Test Telegram connection
    if test_telegram_connection():
        # Send startup notification
        formatter = TelegramFormatter()
        formatter.send_text_only(
            0,
            "NEWSLETTER AUTOMATION SYSTEM ONLINE",
            "GEM Assist automated content delivery activated",
            "The Newsletter Automation System is now connected and ready to deliver content to this channel.",
            "System initialized successfully. All content from the Newsletter Automation will be automatically posted here with professional formatting.",
            None
        )
    
    # Check for pending content
    stats = get_system_stats()
    logger.info(f"📊 System Status:")
    logger.info(f"   Total Content: {stats['total_content']}")
    logger.info(f"   Sent: {stats['sent_content']}")
    logger.info(f"   Pending: {stats['pending_content']}")
    logger.info(f"   With Video: {stats['with_video']}")
    logger.info(f"   With Image: {stats['with_image']}")
    
    # Send any pending content
    send_pending_content()
    
    # Setup scheduler
    setup_scheduler()
    
    logger.info("✅ Newsletter Automation System is operational!")
    
    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 System shutdown")

if __name__ == "__main__":
    main()