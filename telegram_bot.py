import requests
import time
from datetime import datetime, timedelta
from app import app, db
from models import NewsArticle, TelegramMessage, SystemStatus
from config import Config
from utils import rate_limit
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session = requests.Session()
        
    def validate_config(self):
        """Validate Telegram configuration"""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")
        
        # Test bot connection
        try:
            response = self._make_request("getMe")
            if response.get("ok"):
                logger.info(f"Telegram bot connected: {response['result'].get('username')}")
                return True
            else:
                raise ValueError(f"Bot validation failed: {response.get('description')}")
        except Exception as e:
            logger.error(f"Telegram bot validation failed: {e}")
            raise
    
    @rate_limit(max_calls=20, period=60)  # Telegram rate limit: 20 messages per minute
    def send_message(self, text, parse_mode='HTML'):
        """Send message to Telegram with retry logic"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': text[:4096],  # Telegram message limit
                'parse_mode': parse_mode,
                'disable_web_page_preview': False,
                'disable_notification': False
            }
            
            response = self._make_request("sendMessage", payload)
            
            if response.get("ok"):
                return response.get("result")
            else:
                error_msg = response.get("description", "Unknown error")
                logger.error(f"Telegram API error: {error_msg}")
                raise Exception(f"Telegram API error: {error_msg}")
                
        except requests.RequestException as e:
            logger.error(f"Network error sending Telegram message: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            raise
    
    def _make_request(self, method, payload=None):
        """Make request to Telegram API with timeout and error handling"""
        url = f"{self.base_url}/{method}"
        
        try:
            response = self.session.post(
                url, 
                json=payload, 
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Telegram API request failed for {method}: {e}")
            raise
    
    def format_article_message(self, article):
        """Format article for Telegram message"""
        try:
            # Create formatted message
            emoji_map = {
                'threats': '⚠️',
                'security': '🔒',
                'cybersecurity': '🛡️',
                'general': '📰'
            }
            
            emoji = emoji_map.get(article.category, '📰')
            source_name = article.source.title().replace('_', ' ')
            
            message = f"{emoji} <b>{article.title}</b>\n\n"
            
            if article.description:
                # Clean and truncate description
                description = article.description.strip()
                if len(description) > 300:
                    description = description[:297] + "..."
                message += f"{description}\n\n"
            
            message += f"📍 Source: {source_name}\n"
            message += f"🔗 <a href='{article.url}'>Read More</a>"
            
            if len(message) > 4096:  # Telegram limit
                # Truncate if too long
                message = message[:4090] + "..."
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting article message: {e}")
            # Fallback simple format
            return f"📰 {article.title}\n\n🔗 {article.url}"
    
    def send_article(self, article):
        """Send single article to Telegram with retry logic"""
        max_retries = Config.MAX_TELEGRAM_RETRIES
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Format message
                message_text = self.format_article_message(article)
                
                # Send message
                result = self.send_message(message_text)
                
                # Mark as sent in database
                with app.app_context():
                    article.telegram_sent = True
                    article.telegram_sent_at = datetime.utcnow()
                    article.retry_count = retry_count
                    
                    # Create telegram message record
                    telegram_msg = TelegramMessage()
                    telegram_msg.article_id = article.id
                    telegram_msg.message_text = message_text
                    telegram_msg.chat_id = self.chat_id
                    telegram_msg.message_id = str(result.get('message_id', ''))
                    telegram_msg.status = 'sent'
                    telegram_msg.sent_at = datetime.utcnow()
                    telegram_msg.retry_count = retry_count
                    
                    db.session.add(telegram_msg)
                    db.session.commit()
                
                logger.debug(f"Successfully sent article: {article.title[:50]}")
                return True
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Failed to send article (attempt {retry_count}/{max_retries}): {e}"
                logger.warning(error_msg)
                
                if retry_count < max_retries:
                    # Wait before retry
                    time.sleep(Config.RETRY_DELAY_SECONDS)
                else:
                    # Max retries reached, mark as failed
                    with app.app_context():
                        article.retry_count = retry_count
                        
                        # Create failed telegram message record
                        telegram_msg = TelegramMessage()
                        telegram_msg.article_id = article.id
                        telegram_msg.message_text = self.format_article_message(article)
                        telegram_msg.status = 'failed'
                        telegram_msg.error_message = str(e)
                        telegram_msg.retry_count = retry_count
                        
                        db.session.add(telegram_msg)
                        db.session.commit()
                    
                    logger.error(f"Failed to send article after {max_retries} attempts: {article.title}")
                    return False
        
        return False
    
    def send_pending_articles(self):
        """Send all pending articles to Telegram"""
        with app.app_context():
            try:
                logger.info("Starting Telegram message delivery")
                
                # Update system status
                self._update_system_status("telegram_sender", "running")
                
                # Get pending articles (not sent, limited retries)
                pending_articles = NewsArticle.query.filter(
                    NewsArticle.telegram_sent == False,
                    NewsArticle.retry_count < Config.MAX_TELEGRAM_RETRIES,
                    NewsArticle.is_active == True
                ).order_by(NewsArticle.published_at.desc()).limit(20).all()
                
                if not pending_articles:
                    logger.info("No pending articles to send")
                    self._update_system_status(
                        "telegram_sender", 
                        "active", 
                        last_success=datetime.utcnow()
                    )
                    return 0
                
                sent_count = 0
                failed_count = 0
                
                for article in pending_articles:
                    try:
                        if self.send_article(article):
                            sent_count += 1
                        else:
                            failed_count += 1
                        
                        # Small delay between messages to avoid rate limiting
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing article {article.id}: {e}")
                        failed_count += 1
                        continue
                
                # Update system status
                if failed_count == 0:
                    self._update_system_status(
                        "telegram_sender", 
                        "active", 
                        last_success=datetime.utcnow()
                    )
                else:
                    self._update_system_status(
                        "telegram_sender", 
                        "error" if sent_count == 0 else "active",
                        error_message=f"Failed to send {failed_count} articles"
                    )
                
                logger.info(f"Telegram delivery completed: {sent_count} sent, {failed_count} failed")
                return sent_count
                
            except Exception as e:
                error_msg = f"Telegram sender error: {e}"
                logger.error(error_msg)
                self._update_system_status("telegram_sender", "error", error_message=error_msg)
                return 0
    
    def retry_failed_messages(self):
        """Retry failed Telegram messages that are within retry limit"""
        with app.app_context():
            try:
                # Get failed messages that can be retried
                failed_articles = NewsArticle.query.filter(
                    NewsArticle.telegram_sent == False,
                    NewsArticle.retry_count > 0,
                    NewsArticle.retry_count < Config.MAX_TELEGRAM_RETRIES,
                    NewsArticle.is_active == True
                ).all()
                
                retry_count = 0
                for article in failed_articles:
                    if self.send_article(article):
                        retry_count += 1
                    time.sleep(3)  # Longer delay for retries
                
                if retry_count > 0:
                    logger.info(f"Successfully retried {retry_count} failed messages")
                
                return retry_count
                
            except Exception as e:
                logger.error(f"Error retrying failed messages: {e}")
                return 0
    
    def _update_system_status(self, component, status, last_success=None, error_message=None):
        """Update system status in database"""
        try:
            system_status = SystemStatus.query.filter_by(component=component).first()
            
            if not system_status:
                system_status = SystemStatus()
                system_status.component = component
                db.session.add(system_status)
            
            system_status.status = status
            system_status.last_run = datetime.utcnow()
            system_status.updated_at = datetime.utcnow()
            
            if last_success:
                system_status.last_success = last_success
                system_status.error_count = 0
            
            if error_message:
                system_status.error_count += 1
                system_status.last_error = error_message
                system_status.last_error_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update system status for {component}: {e}")
            db.session.rollback()
