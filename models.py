from datetime import datetime
from app import db
from sqlalchemy import Index
import logging

logger = logging.getLogger(__name__)

class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(512), nullable=False)
    url = db.Column(db.String(2048), nullable=False, unique=True)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    source = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), default='general')
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    telegram_sent = db.Column(db.Boolean, default=False)
    telegram_sent_at = db.Column(db.DateTime)
    retry_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_source_published', 'source', 'published_at'),
        Index('idx_telegram_sent', 'telegram_sent'),
        Index('idx_collected_at', 'collected_at'),
        Index('idx_url_hash', 'url'),
    )
    
    def __repr__(self):
        return f'<NewsArticle {self.title[:50]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'source': self.source,
            'category': self.category,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'telegram_sent': self.telegram_sent
        }

class SystemStatus(db.Model):
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    component = db.Column(db.String(128), nullable=False, unique=True)
    status = db.Column(db.String(32), nullable=False)  # active, error, disabled
    last_run = db.Column(db.DateTime)
    last_success = db.Column(db.DateTime)
    error_count = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text)
    last_error_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemStatus {self.component}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'component': self.component,
            'status': self.status,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None
        }

class TelegramMessage(db.Model):
    __tablename__ = 'telegram_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    chat_id = db.Column(db.String(64))
    message_id = db.Column(db.String(64))
    status = db.Column(db.String(32), default='pending')  # pending, sent, failed
    retry_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    article = db.relationship('NewsArticle', backref=db.backref('telegram_messages', lazy=True))
    
    def __repr__(self):
        return f'<TelegramMessage {self.id}: {self.status}>'
