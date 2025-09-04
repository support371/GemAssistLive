#!/usr/bin/env python3
"""
Simple Flask wrapper for GemFeed system status monitoring
"""
from flask import Flask, jsonify, render_template_string
import threading
import time
from gemfeed_simple import (
    init_db, setup_cybersecurity_feeds, run_collection_cycle, 
    get_system_stats, test_telegram_connection, setup_scheduler
)

app = Flask(__name__)

# Initialize GemFeed in background
def initialize_gemfeed():
    """Initialize GemFeed system in background"""
    try:
        init_db()
        setup_cybersecurity_feeds()
        test_telegram_connection()
        
        # Run initial collection
        run_collection_cycle()
        
        # Setup automated scheduling
        setup_scheduler()
        
    except Exception as e:
        print(f"Error initializing GemFeed: {e}")

# Start GemFeed in background thread
init_thread = threading.Thread(target=initialize_gemfeed, daemon=True)
init_thread.start()

@app.route('/')
def dashboard():
    """Simple dashboard showing system status"""
    try:
        stats = get_system_stats()
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>GemFeed - Cybersecurity News System</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%); min-height: 100vh; }
        .cyber-card { background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; backdrop-filter: blur(10px); }
        .status-active { color: #10b981; }
        .status-pending { color: #f59e0b; }
        .cyber-title { background: linear-gradient(45deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="row mb-4">
            <div class="col-12 text-center">
                <h1 class="display-4 fw-bold cyber-title mb-2">🔒 GemFeed</h1>
                <p class="text-light">Cybersecurity News Aggregation System</p>
            </div>
        </div>
        
        <div class="row g-4">
            <div class="col-md-3">
                <div class="card cyber-card">
                    <div class="card-body text-center">
                        <h2 class="display-6 status-active">{{ stats.active_feeds }}</h2>
                        <p class="text-muted mb-0">📡 Active Feeds</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card cyber-card">
                    <div class="card-body text-center">
                        <h2 class="display-6 text-light">{{ stats.total_articles }}</h2>
                        <p class="text-muted mb-0">📰 Total Articles</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card cyber-card">
                    <div class="card-body text-center">
                        <h2 class="display-6 status-active">{{ stats.sent_articles }}</h2>
                        <p class="text-muted mb-0">✅ Sent to Telegram</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card cyber-card">
                    <div class="card-body text-center">
                        <h2 class="display-6 status-pending">{{ stats.pending_articles }}</h2>
                        <p class="text-muted mb-0">⏳ Pending Delivery</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-5">
            <div class="col-12">
                <div class="card cyber-card">
                    <div class="card-body">
                        <h3 class="text-light mb-4">🚀 System Status</h3>
                        <div class="row">
                            <div class="col-md-6">
                                <p><span class="status-active">✅</span> <strong>Database:</strong> Operational</p>
                                <p><span class="status-active">✅</span> <strong>RSS Collection:</strong> Every 15 minutes</p>
                                <p><span class="status-active">✅</span> <strong>Telegram Bot:</strong> @GEMAssist_bot</p>
                            </div>
                            <div class="col-md-6">
                                <p><span class="status-active">✅</span> <strong>News Sources:</strong> 7 cybersecurity feeds</p>
                                <p><span class="status-active">✅</span> <strong>Auto-Delivery:</strong> Active</p>
                                <p><span class="status-active">✅</span> <strong>Rate Limiting:</strong> Telegram-safe</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-12 text-center">
                <p class="text-muted">
                    📱 Delivering cybersecurity news to: 
                    <strong>LEGALIZED (CYBERSECURE & WEALTH -WELLBEING NETWORK)</strong>
                </p>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        """, stats=stats)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'})

@app.route('/api/stats')
def api_stats():
    """API endpoint for system statistics"""
    try:
        stats = get_system_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/collect')
def api_collect():
    """Manual trigger for news collection"""
    try:
        def run_collection():
            run_collection_cycle()
        
        collection_thread = threading.Thread(target=run_collection, daemon=True)
        collection_thread.start()
        
        return jsonify({'status': 'started', 'message': 'Collection cycle started'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)