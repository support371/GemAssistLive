import time
import hashlib
import re
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def rate_limit(max_calls, period):
    """Rate limiting decorator"""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls outside the period
            calls[:] = [call for call in calls if now - call < period]
            
            if len(calls) >= max_calls:
                sleep_time = period - (now - calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
            
            calls.append(time.time())
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' ',
        '&mdash;': '—',
        '&ndash;': '–',
        '&ldquo;': '"',
        '&rdquo;': '"',
        '&lsquo;': "'",
        '&rsquo;': "'"
    }
    
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def calculate_hash(text):
    """Calculate MD5 hash of text for duplicate detection"""
    if not text:
        return ""
    
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return "Never"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 7:
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def truncate_text(text, max_length=100):
    """Truncate text to specified length"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def get_status_color(status):
    """Get Bootstrap color class for status"""
    status_colors = {
        'active': 'success',
        'running': 'primary',
        'error': 'danger',
        'disabled': 'secondary',
        'warning': 'warning'
    }
    return status_colors.get(status, 'secondary')

def safe_get(dictionary, key, default=None):
    """Safely get value from dictionary"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.debug(f"{func.__name__} executed in {execution_time:.2f} seconds")
        
        return result
    return wrapper

def validate_url(url):
    """Basic URL validation"""
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def create_error_response(message, status_code=500):
    """Create standardized error response"""
    return {
        'success': False,
        'error': message,
        'timestamp': datetime.utcnow().isoformat()
    }, status_code

def create_success_response(data=None, message=None):
    """Create standardized success response"""
    response = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return response
