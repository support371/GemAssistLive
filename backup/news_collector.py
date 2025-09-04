import feedparser
import requests
from datetime import datetime, timedelta
from app import app, db
from models import NewsArticle, SystemStatus
from config import Config
from utils import rate_limit, clean_text, calculate_hash
import logging
import time

logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GemFeed-NewsBot/1.0 (Cybersecurity News Aggregator)'
        })
        
    @rate_limit(max_calls=Config.MAX_REQUESTS_PER_MINUTE, period=60)
    def collect_from_source(self, source_name, source_config):
        """Collect news from a single source with error handling"""
        with app.app_context():
            try:
                logger.info(f"Collecting news from {source_name}")
                
                # Update system status
                self._update_system_status(f"news_collector_{source_name}", "running")
                
                if source_config['type'] == 'rss':
                    articles = self._collect_rss_feed(source_name, source_config)
                else:
                    logger.warning(f"Unsupported source type: {source_config['type']}")
                    return 0
                
                saved_count = self._save_articles(articles, source_name, source_config['category'])
                
                # Update success status
                self._update_system_status(
                    f"news_collector_{source_name}", 
                    "active", 
                    last_success=datetime.utcnow()
                )
                
                logger.info(f"Successfully collected {saved_count} new articles from {source_name}")
                return saved_count
                
            except Exception as e:
                error_msg = f"Failed to collect from {source_name}: {str(e)}"
                logger.error(error_msg)
                
                # Update error status
                self._update_system_status(
                    f"news_collector_{source_name}", 
                    "error", 
                    error_message=error_msg
                )
                return 0
    
    def _collect_rss_feed(self, source_name, source_config):
        """Collect articles from RSS feed"""
        try:
            # Use requests with timeout
            response = self.session.get(
                source_config['url'], 
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing issues for {source_name}: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries[:Config.MAX_ARTICLES_PER_BATCH]:
                try:
                    article = self._parse_rss_entry(entry, source_name)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse entry from {source_name}: {e}")
                    continue
            
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Network error collecting from {source_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS from {source_name}: {e}")
            raise
    
    def _parse_rss_entry(self, entry, source_name):
        """Parse a single RSS entry into article data"""
        try:
            # Extract basic information
            title = clean_text(getattr(entry, 'title', ''))
            url = getattr(entry, 'link', '')
            description = clean_text(getattr(entry, 'summary', ''))
            
            if not title or not url:
                logger.warning(f"Skipping entry with missing title or URL from {source_name}")
                return None
            
            # Parse published date
            published_at = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid published date for entry from {source_name}")
            
            if not published_at:
                published_at = datetime.utcnow()
            
            # Extract content if available
            content = ''
            if hasattr(entry, 'content'):
                content = clean_text(' '.join([c.value for c in entry.content]))
            elif hasattr(entry, 'summary'):
                content = description
            
            return {
                'title': title[:512],  # Truncate to database limit
                'url': url[:2048],    # Truncate to database limit
                'description': description[:1000] if description else '',
                'content': content[:5000] if content else '',  # Reasonable content limit
                'published_at': published_at,
                'source': source_name
            }
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry from {source_name}: {e}")
            return None
    
    def _save_articles(self, articles, source_name, category):
        """Save articles to database with duplicate checking"""
        saved_count = 0
        
        try:
            for article_data in articles:
                try:
                    # Check if article already exists
                    existing = NewsArticle.query.filter_by(url=article_data['url']).first()
                    
                    if existing:
                        logger.debug(f"Article already exists: {article_data['title'][:50]}")
                        continue
                    
                    # Create new article
                    article = NewsArticle()
                    article.title = article_data['title']
                    article.url = article_data['url']
                    article.description = article_data['description']
                    article.content = article_data['content']
                    article.source = source_name
                    article.category = category
                    article.published_at = article_data['published_at']
                    article.collected_at = datetime.utcnow()
                    
                    db.session.add(article)
                    saved_count += 1
                    
                    # Commit in batches to avoid memory issues
                    if saved_count % 10 == 0:
                        db.session.commit()
                        logger.debug(f"Committed batch of 10 articles from {source_name}")
                    
                except Exception as e:
                    logger.error(f"Error saving article from {source_name}: {e}")
                    db.session.rollback()
                    continue
            
            # Final commit
            if saved_count > 0:
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Database error saving articles from {source_name}: {e}")
            db.session.rollback()
            raise
        
        return saved_count
    
    def collect_all_sources(self):
        """Collect news from all enabled sources"""
        total_collected = 0
        
        with app.app_context():
            logger.info("Starting news collection from all sources")
            
            for source_name, source_config in Config.NEWS_SOURCES.items():
                if not source_config.get('enabled', False):
                    logger.info(f"Skipping disabled source: {source_name}")
                    continue
                
                try:
                    count = self.collect_from_source(source_name, source_config)
                    total_collected += count
                    
                    # Small delay between sources to be respectful
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to collect from {source_name}: {e}")
                    continue
            
            logger.info(f"News collection completed. Total new articles: {total_collected}")
            return total_collected
    
    def cleanup_old_articles(self):
        """Remove old articles to manage database size"""
        with app.app_context():
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=Config.MAX_ARTICLES_RETENTION_DAYS)
                
                deleted_count = db.session.query(NewsArticle).filter(
                    NewsArticle.collected_at < cutoff_date
                ).delete()
                
                db.session.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old articles")
                    
                return deleted_count
                
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                db.session.rollback()
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
                system_status.error_count = 0  # Reset error count on success
            
            if error_message:
                system_status.error_count += 1
                system_status.last_error = error_message
                system_status.last_error_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update system status for {component}: {e}")
            db.session.rollback()
