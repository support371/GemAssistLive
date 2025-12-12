#!/usr/bin/env python3
"""
GEM Newsletter Automation - Web Dashboard
Manages newsletter content and Telegram delivery
"""
from flask import Flask, jsonify, render_template_string, request, redirect, url_for
import threading
import time
from newsletter_system import (
    init_db, add_content, get_all_content, get_unsent_content,
    send_pending_content, get_system_stats, test_telegram_connection, 
    setup_scheduler, TelegramFormatter, add_sample_content
)

app = Flask(__name__)
app.secret_key = 'gem-newsletter-secret-key'

# Initialize Newsletter System in background
def initialize_newsletter():
    """Initialize Newsletter system in background"""
    try:
        init_db()
        test_telegram_connection()
        
        # Send startup notification
        formatter = TelegramFormatter()
        formatter.send_text_only(
            0,
            "NEWSLETTER AUTOMATION SYSTEM ONLINE",
            "GEM Assist automated content delivery activated",
            "The Newsletter Automation System is now connected to your Telegram channel.",
            "All newsletter content will be automatically posted with professional formatting including logos, images, and videos.",
            None
        )
        
        # Check for pending content and send
        send_pending_content()
        
        # Setup automated scheduling
        setup_scheduler()
        
    except Exception as e:
        print(f"Error initializing Newsletter system: {e}")

# Start newsletter system in background thread
init_thread = threading.Thread(target=initialize_newsletter, daemon=True)
init_thread.start()

dashboard_template = """
<!DOCTYPE html>
<html>
<head>
    <title>GEM Newsletter Automation</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Vercel Web Analytics -->
    <script defer src="https://cdn.vercel-analytics.com/v1/web.js"></script>
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%); min-height: 100vh; }
        .cyber-card { background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; backdrop-filter: blur(10px); border-radius: 12px; }
        .status-active { color: #10b981; }
        .status-pending { color: #f59e0b; }
        .status-sent { color: #06b6d4; }
        .cyber-title { background: linear-gradient(45deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .btn-cyber { background: linear-gradient(45deg, #06b6d4, #3b82f6); border: none; color: white; }
        .btn-cyber:hover { background: linear-gradient(45deg, #0891b2, #2563eb); color: white; }
        .content-item { border-left: 3px solid #06b6d4; padding-left: 15px; margin-bottom: 20px; }
        .content-item.sent { border-left-color: #10b981; }
        .content-item.pending { border-left-color: #f59e0b; }
        .media-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; }
        .badge-video { background: #dc2626; }
        .badge-image { background: #7c3aed; }
        .badge-text { background: #6b7280; }
    </style>
</head>
<body>
    <div class="container py-5">
        <!-- Header -->
        <div class="row mb-4">
            <div class="col-12 text-center">
                <h1 class="display-4 fw-bold cyber-title mb-2">
                    <i class="fas fa-newspaper me-2"></i>GEM Newsletter Automation
                </h1>
                <p class="text-light">Automated Content Delivery to Telegram</p>
                <p class="text-muted">Channel: <strong>@CyberWealthSecure</strong></p>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div class="row g-4 mb-5">
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 text-light">{{ stats.total_content }}</h2>
                        <p class="text-muted mb-0"><i class="fas fa-file-alt me-1"></i> Total</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 status-sent">{{ stats.sent_content }}</h2>
                        <p class="text-muted mb-0"><i class="fas fa-check-circle me-1"></i> Sent</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 status-pending">{{ stats.pending_content }}</h2>
                        <p class="text-muted mb-0"><i class="fas fa-clock me-1"></i> Pending</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 text-danger">{{ stats.with_video }}</h2>
                        <p class="text-muted mb-0"><i class="fas fa-video me-1"></i> Videos</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 text-purple" style="color: #a855f7;">{{ stats.with_image }}</h2>
                        <p class="text-muted mb-0"><i class="fas fa-image me-1"></i> Images</p>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card cyber-card">
                    <div class="card-body text-center py-4">
                        <h2 class="display-6 status-active"><i class="fas fa-check"></i></h2>
                        <p class="text-muted mb-0"><i class="fab fa-telegram me-1"></i> Connected</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="row mb-5">
            <div class="col-12">
                <div class="card cyber-card">
                    <div class="card-body d-flex justify-content-center gap-3 py-4">
                        <a href="/add" class="btn btn-cyber btn-lg">
                            <i class="fas fa-plus me-2"></i>Add Content
                        </a>
                        <button onclick="sendNow()" class="btn btn-success btn-lg">
                            <i class="fab fa-telegram me-2"></i>Send Now
                        </button>
                        <button onclick="addSamples()" class="btn btn-outline-light btn-lg">
                            <i class="fas fa-flask me-2"></i>Add Samples
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Content List -->
        <div class="row">
            <div class="col-12">
                <div class="card cyber-card">
                    <div class="card-header bg-transparent border-bottom border-secondary">
                        <h3 class="text-light mb-0"><i class="fas fa-list me-2"></i>Newsletter Content</h3>
                    </div>
                    <div class="card-body">
                        {% if content_list %}
                            {% for item in content_list %}
                            <div class="content-item {{ 'sent' if item[10] else 'pending' }}">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h5 class="text-light mb-0">{{ item[1] }}</h5>
                                    <div>
                                        {% if item[6] %}
                                        <span class="badge badge-video media-badge">VIDEO</span>
                                        {% elif item[5] %}
                                        <span class="badge badge-image media-badge">IMAGE</span>
                                        {% else %}
                                        <span class="badge badge-text media-badge">TEXT</span>
                                        {% endif %}
                                        
                                        {% if item[10] %}
                                        <span class="badge bg-success ms-1">SENT</span>
                                        {% else %}
                                        <span class="badge bg-warning text-dark ms-1">PENDING</span>
                                        {% endif %}
                                    </div>
                                </div>
                                {% if item[2] %}
                                <p class="text-muted fst-italic mb-2">{{ item[2] }}</p>
                                {% endif %}
                                {% if item[3] %}
                                <p class="text-light mb-2">{{ item[3][:200] }}{% if item[3]|length > 200 %}...{% endif %}</p>
                                {% endif %}
                                <small class="text-muted">
                                    <i class="fas fa-calendar me-1"></i>{{ item[9] }}
                                    {% if item[11] %}
                                    | <i class="fab fa-telegram me-1"></i>Sent: {{ item[11] }}
                                    {% endif %}
                                </small>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="text-center py-5">
                                <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                                <p class="text-muted">No content yet. Add your first newsletter item!</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="row mt-5">
            <div class="col-12 text-center">
                <p class="text-muted">
                    <i class="fas fa-robot me-1"></i> Automated delivery every 5 minutes
                    | <i class="fab fa-telegram me-1"></i> @GEMAssist_bot
                </p>
            </div>
        </div>
    </div>
    
    <script>
        function sendNow() {
            fetch('/api/send')
                .then(r => r.json())
                .then(d => {
                    alert(d.message || 'Sending started!');
                    location.reload();
                });
        }
        
        function addSamples() {
            fetch('/api/samples')
                .then(r => r.json())
                .then(d => {
                    alert(d.message || 'Samples added!');
                    location.reload();
                });
        }
        
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

add_content_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Add Newsletter Content - GEM</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%); min-height: 100vh; }
        .cyber-card { background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; backdrop-filter: blur(10px); border-radius: 12px; }
        .cyber-title { background: linear-gradient(45deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .btn-cyber { background: linear-gradient(45deg, #06b6d4, #3b82f6); border: none; color: white; }
        .btn-cyber:hover { background: linear-gradient(45deg, #0891b2, #2563eb); color: white; }
        .form-control, .form-select { background: rgba(30, 41, 59, 0.8); border: 1px solid #475569; color: white; }
        .form-control:focus, .form-select:focus { background: rgba(30, 41, 59, 0.9); border-color: #06b6d4; color: white; box-shadow: 0 0 0 0.2rem rgba(6, 182, 212, 0.25); }
        .form-control::placeholder { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card cyber-card">
                    <div class="card-header bg-transparent border-bottom border-secondary">
                        <h2 class="cyber-title mb-0">
                            <i class="fas fa-plus-circle me-2"></i>Add Newsletter Content
                        </h2>
                    </div>
                    <div class="card-body p-4">
                        <form method="POST" action="/add">
                            <div class="mb-3">
                                <label class="form-label text-light">Title *</label>
                                <input type="text" name="title" class="form-control" placeholder="Main headline" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label text-light">Subheading</label>
                                <input type="text" name="subheading" class="form-control" placeholder="Secondary headline or context">
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label text-light">Summary</label>
                                <textarea name="summary" class="form-control" rows="2" placeholder="Brief summary (shown prominently)"></textarea>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label text-light">Full Content</label>
                                <textarea name="full_content" class="form-control" rows="5" placeholder="Complete article text"></textarea>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label text-light"><i class="fas fa-image me-1"></i> Image URL</label>
                                    <input type="url" name="image_url" class="form-control" placeholder="https://...">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label text-light"><i class="fas fa-video me-1"></i> Video URL</label>
                                    <input type="url" name="video_url" class="form-control" placeholder="https://...">
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label text-light">Logo URL</label>
                                    <input type="url" name="logo_url" class="form-control" placeholder="Company/brand logo URL">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label text-light">Category</label>
                                    <select name="category" class="form-select">
                                        <option value="general">General</option>
                                        <option value="cybersecurity">Cybersecurity</option>
                                        <option value="technology">Technology</option>
                                        <option value="finance">Finance</option>
                                        <option value="health">Health & Wellness</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="d-flex gap-3 mt-4">
                                <button type="submit" class="btn btn-cyber btn-lg">
                                    <i class="fas fa-save me-2"></i>Save & Queue for Telegram
                                </button>
                                <a href="/" class="btn btn-outline-light btn-lg">
                                    <i class="fas fa-arrow-left me-2"></i>Back
                                </a>
                            </div>
                        </form>
                    </div>
                </div>
                
                <!-- Preview Card -->
                <div class="card cyber-card mt-4">
                    <div class="card-header bg-transparent border-bottom border-secondary">
                        <h5 class="text-light mb-0"><i class="fab fa-telegram me-2"></i>Telegram Preview Format</h5>
                    </div>
                    <div class="card-body">
                        <div class="bg-dark p-3 rounded" style="font-family: monospace; font-size: 0.9rem;">
                            <p class="text-info mb-1">🔒 <strong>GEM ASSIST</strong></p>
                            <p class="text-light mb-1">📰 <strong>[TITLE IN CAPS]</strong></p>
                            <p class="text-muted mb-2"><em>[Subheading]</em></p>
                            <p class="text-secondary mb-1">[Video or Image here]</p>
                            <p class="text-light mb-1">📋 <strong>SUMMARY:</strong> [summary text]</p>
                            <p class="text-light mb-1">📄 <strong>FULL CONTENT:</strong> [content text]</p>
                            <p class="text-muted mb-0">━━━━━━━━━━━━━━━━━</p>
                            <p class="text-info mb-0">📱 @CyberWealthSecure</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard showing system status and content"""
    try:
        stats = get_system_stats()
        content_list = get_all_content(20)
        return render_template_string(dashboard_template, stats=stats, content_list=content_list)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'})

@app.route('/add', methods=['GET', 'POST'])
def add_content_page():
    """Add new newsletter content"""
    if request.method == 'POST':
        try:
            content_id = add_content(
                title=request.form.get('title'),
                subheading=request.form.get('subheading'),
                summary=request.form.get('summary'),
                full_content=request.form.get('full_content'),
                image_url=request.form.get('image_url') or None,
                video_url=request.form.get('video_url') or None,
                logo_url=request.form.get('logo_url') or None,
                category=request.form.get('category', 'general'),
                source='web'
            )
            return redirect(url_for('dashboard'))
        except Exception as e:
            return jsonify({'error': str(e)})
    
    return render_template_string(add_content_template)

@app.route('/api/stats')
def api_stats():
    """API endpoint for system statistics"""
    try:
        stats = get_system_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/send')
def api_send():
    """Trigger immediate content delivery to Telegram"""
    try:
        def run_send():
            send_pending_content()
        
        send_thread = threading.Thread(target=run_send, daemon=True)
        send_thread.start()
        
        return jsonify({'status': 'started', 'message': 'Sending content to Telegram...'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/samples')
def api_samples():
    """Add sample content for testing"""
    try:
        add_sample_content()
        return jsonify({'status': 'success', 'message': 'Sample content added!'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/content')
def api_content():
    """Get all content as JSON"""
    try:
        content = get_all_content(50)
        return jsonify([{
            'id': c[0],
            'title': c[1],
            'subheading': c[2],
            'summary': c[3],
            'full_content': c[4],
            'image_url': c[5],
            'video_url': c[6],
            'logo_url': c[7],
            'category': c[8],
            'created_at': c[9],
            'telegram_sent': c[10],
            'telegram_sent_at': c[11]
        } for c in content])
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)