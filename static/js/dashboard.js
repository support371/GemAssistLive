// Dashboard JavaScript functionality
class GemFeedDashboard {
    constructor() {
        this.init();
        this.startAutoRefresh();
    }
    
    init() {
        // Initialize event listeners
        this.bindEvents();
        
        // Update timestamps
        this.updateTimestamps();
        
        // Initialize tooltips
        this.initTooltips();
        
        console.log('GemFeed Dashboard initialized');
    }
    
    bindEvents() {
        // Manual collection button
        const collectBtn = document.getElementById('collectBtn');
        if (collectBtn) {
            collectBtn.addEventListener('click', () => this.triggerCollection());
        }
        
        // Manual Telegram send button
        const sendTelegramBtn = document.getElementById('sendTelegramBtn');
        if (sendTelegramBtn) {
            sendTelegramBtn.addEventListener('click', () => this.triggerTelegramSend());
        }

        // Refresh feeds button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }
        
        // Auto-refresh toggle (could be added to UI)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.refreshDashboard();
            }
        });
    }
    
    async triggerCollection() {
        const collectBtn = document.getElementById('collectBtn');
        const originalText = collectBtn.innerHTML;
        
        try {
            // Update button state
            collectBtn.disabled = true;
            collectBtn.innerHTML = '<i data-feather="loader" width="16" height="16" class="me-1 spinner"></i>Collecting...';
            feather.replace();
            
            const response = await GemFeed.makeRequest('/api/manual/collect', {
                method: 'POST'
            });
            
            if (response.success) {
                GemFeed.showAlert(`Successfully collected ${response.count} new articles`, 'success');
                
                // Refresh dashboard after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                throw new Error(response.error || 'Collection failed');
            }
            
        } catch (error) {
            console.error('Collection failed:', error);
            GemFeed.showAlert(`Collection failed: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            collectBtn.disabled = false;
            collectBtn.innerHTML = originalText;
            feather.replace();
        }
    }
    
    async triggerTelegramSend() {
        const sendTelegramBtn = document.getElementById('sendTelegramBtn');
        const originalText = sendTelegramBtn.innerHTML;
        
        try {
            // Update button state
            sendTelegramBtn.disabled = true;
            sendTelegramBtn.innerHTML = '<i data-feather="loader" width="16" height="16" class="me-1 spinner"></i>Sending...';
            feather.replace();
            
            const response = await GemFeed.makeRequest('/api/manual/telegram', {
                method: 'POST'
            });
            
            if (response.success) {
                GemFeed.showAlert(`Successfully sent ${response.count} Telegram messages`, 'success');
                
                // Refresh dashboard after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                throw new Error(response.error || 'Telegram send failed');
            }
            
        } catch (error) {
            console.error('Telegram send failed:', error);
            GemFeed.showAlert(`Telegram send failed: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            sendTelegramBtn.disabled = false;
            sendTelegramBtn.innerHTML = originalText;
            feather.replace();
        }
    }
    
    async refreshDashboard() {
        try {
            // Show refresh indicator
            const refreshIndicator = this.createRefreshIndicator();
            document.body.appendChild(refreshIndicator);
            
            // Refresh stats and status
            await Promise.all([
                this.refreshStats(),
                this.refreshSystemStatus()
            ]);
            
            GemFeed.showAlert('Dashboard refreshed', 'info');
            
        } catch (error) {
            console.error('Dashboard refresh failed:', error);
            GemFeed.showAlert('Dashboard refresh failed', 'warning');
        } finally {
            // Remove refresh indicator
            const indicator = document.querySelector('.refresh-indicator');
            if (indicator) {
                indicator.remove();
            }
        }
    }
    
    async refreshStats() {
        try {
            const response = await GemFeed.makeRequest('/api/stats');
            
            if (response.success) {
                this.updateStatsCards(response.stats);
            }
        } catch (error) {
            console.error('Failed to refresh stats:', error);
        }
    }
    
    async refreshSystemStatus() {
        try {
            const response = await GemFeed.makeRequest('/api/status');
            
            if (response.success) {
                this.updateSystemStatusTable(response.statuses);
            }
        } catch (error) {
            console.error('Failed to refresh system status:', error);
        }
    }
    
    updateStatsCards(stats) {
        // Update statistics cards
        const statsMapping = {
            'total_articles': 'Total Articles',
            'articles_today': 'Today',
            'pending_telegram': 'Pending Telegram',
            'failed_articles': 'Failed'
        };
        
        Object.keys(statsMapping).forEach(key => {
            const element = document.querySelector(`[data-stat="${key}"] .h4`);
            if (element && stats[key] !== undefined) {
                element.textContent = stats[key];
            }
        });
    }
    
    updateSystemStatusTable(statuses) {
        // This would update the system status table
        // For now, we'll just log the update
        console.log('System status updated:', statuses);
    }
    
    updateTimestamps() {
        // Update all timestamp elements
        const timestampElements = document.querySelectorAll('[data-timestamp]');
        
        timestampElements.forEach(element => {
            const timestamp = element.getAttribute('data-timestamp');
            if (timestamp) {
                const formattedTime = GemFeed.formatDateTime(timestamp);
                element.textContent = formattedTime;
                element.setAttribute('title', new Date(timestamp).toLocaleString());
            }
        });
    }
    
    initTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    createRefreshIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'refresh-indicator position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        indicator.style.backgroundColor = 'rgba(0,0,0,0.5)';
        indicator.style.zIndex = '9999';
        indicator.innerHTML = `
            <div class="bg-dark text-white p-3 rounded">
                <i data-feather="refresh-cw" class="spinner me-2"></i>
                Refreshing dashboard...
            </div>
        `;
        
        // Replace feather icons
        setTimeout(() => feather.replace(), 0);
        
        return indicator;
    }
    
    startAutoRefresh() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.updateTimestamps();
        }, 30000);
        
        // Auto-refresh stats every 2 minutes
        setInterval(() => {
            this.refreshStats();
        }, 120000);
        
        console.log('Auto-refresh started');
    }
}

// Custom CSS for spinner animation
const style = document.createElement('style');
style.textContent = `
    .spinner {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .refresh-indicator {
        backdrop-filter: blur(2px);
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new GemFeedDashboard();
});

// Handle visibility change to pause/resume auto-refresh
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && window.dashboard) {
        // Refresh when tab becomes visible
        window.dashboard.updateTimestamps();
        window.dashboard.refreshStats();
    }
});
