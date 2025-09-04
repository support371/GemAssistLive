from flask import render_template, jsonify, request, flash, redirect, url_for
from app import app, db
from models import NewsArticle, SystemStatus, TelegramMessage
# Avoid circular imports - import scheduler functions when needed
from config import Config
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@app.route('/')
def dashboard():
    """Main dashboard showing system status and recent articles"""
    try:
        # Get system status
        system_statuses = SystemStatus.query.all()
        
        # Get recent articles
        recent_articles = NewsArticle.query.filter_by(is_active=True)\
            .order_by(NewsArticle.collected_at.desc())\
            .limit(10).all()
        
        # Get statistics
        stats = {
            'total_articles': NewsArticle.query.filter_by(is_active=True).count(),
            'articles_today': NewsArticle.query.filter(
                NewsArticle.collected_at >= datetime.utcnow().date()
            ).count(),
            'pending_telegram': NewsArticle.query.filter_by(
                telegram_sent=False, is_active=True
            ).count(),
            'failed_articles': NewsArticle.query.filter(
                NewsArticle.retry_count >= Config.MAX_TELEGRAM_RETRIES,
                NewsArticle.telegram_sent == False
            ).count()
        }
        
        # Get job status from scheduler
        try:
            from scheduler import get_scheduler
            scheduler = get_scheduler()
            jobs = scheduler.get_job_status() if scheduler else []
        except ImportError:
            jobs = []
        
        return render_template('dashboard.html', 
                             system_statuses=system_statuses,
                             recent_articles=recent_articles,
                             stats=stats,
                             jobs=jobs)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', error=str(e))

@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    try:
        system_statuses = SystemStatus.query.all()
        statuses = [status.to_dict() for status in system_statuses]
        
        return jsonify({
            'success': True,
            'statuses': statuses,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for system statistics"""
    try:
        stats = {
            'total_articles': NewsArticle.query.filter_by(is_active=True).count(),
            'articles_today': NewsArticle.query.filter(
                NewsArticle.collected_at >= datetime.utcnow().date()
            ).count(),
            'articles_this_week': NewsArticle.query.filter(
                NewsArticle.collected_at >= datetime.utcnow() - timedelta(days=7)
            ).count(),
            'pending_telegram': NewsArticle.query.filter_by(
                telegram_sent=False, is_active=True
            ).count(),
            'sent_telegram': NewsArticle.query.filter_by(
                telegram_sent=True
            ).count(),
            'failed_articles': NewsArticle.query.filter(
                NewsArticle.retry_count >= Config.MAX_TELEGRAM_RETRIES,
                NewsArticle.telegram_sent == False
            ).count()
        }
        
        # Source statistics
        source_stats = {}
        for source_name in Config.NEWS_SOURCES.keys():
            source_stats[source_name] = NewsArticle.query.filter_by(source=source_name).count()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'source_stats': source_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/articles')
def api_articles():
    """API endpoint for articles with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        source = request.args.get('source')
        sent_only = request.args.get('sent_only', type=bool)
        
        query = NewsArticle.query.filter_by(is_active=True)
        
        if source:
            query = query.filter_by(source=source)
        
        if sent_only is not None:
            query = query.filter_by(telegram_sent=sent_only)
        
        query = query.order_by(NewsArticle.collected_at.desc())
        
        articles = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'articles': [article.to_dict() for article in articles.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': articles.total,
                'pages': articles.pages,
                'has_next': articles.has_next,
                'has_prev': articles.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"API articles error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/manual/collect', methods=['POST'])
def api_manual_collect():
    """Manually trigger news collection"""
    try:
        try:
            from scheduler import get_scheduler
            scheduler = get_scheduler()
            if not scheduler:
                return jsonify({'success': False, 'error': 'Scheduler not available'}), 500
            
            count = scheduler.run_immediate_collection()
        except ImportError:
            return jsonify({'success': False, 'error': 'Scheduler not available'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Collected {count} new articles',
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Manual collection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/manual/telegram', methods=['POST'])
def api_manual_telegram():
    """Manually trigger Telegram sending"""
    try:
        try:
            from scheduler import get_scheduler
            scheduler = get_scheduler()
            if not scheduler:
                return jsonify({'success': False, 'error': 'Scheduler not available'}), 500
            
            count = scheduler.run_immediate_telegram_send()
        except ImportError:
            return jsonify({'success': False, 'error': 'Scheduler not available'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Sent {count} Telegram messages',
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Manual Telegram send error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/articles')
def articles_page():
    """Articles listing page"""
    try:
        page = request.args.get('page', 1, type=int)
        source = request.args.get('source')
        
        query = NewsArticle.query.filter_by(is_active=True)
        
        if source:
            query = query.filter_by(source=source)
        
        articles = query.order_by(NewsArticle.collected_at.desc()).paginate(
            page=page, 
            per_page=20, 
            error_out=False
        )
        
        sources = list(Config.NEWS_SOURCES.keys())
        
        return render_template('articles.html', 
                             articles=articles,
                             sources=sources,
                             current_source=source)
        
    except Exception as e:
        logger.error(f"Articles page error: {e}")
        flash(f'Error loading articles: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Basic database connectivity test
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500
