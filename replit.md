# Overview

GemFeed is a cybersecurity news aggregation system that automatically collects news articles from various RSS feeds, stores them in a database, and distributes them via Telegram. The application serves as an automated news monitoring and distribution platform focused on cybersecurity content from sources like ThreatPost, KrebsOnSecurity, Dark Reading, Bleeping Computer, Security Week, and The Hacker News.

The system features a web dashboard for monitoring and management, background job scheduling for automated collection and distribution, and robust error handling with retry mechanisms.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Flask Web Framework**: Chosen for its simplicity and flexibility in building the web interface and API endpoints
- **SQLAlchemy ORM**: Provides database abstraction layer with support for multiple database backends
- **Background Scheduler**: Uses APScheduler for automated news collection and Telegram distribution tasks

## Database Design
- **Single Database Architecture**: Uses SQLAlchemy with support for both SQLite (development) and PostgreSQL (production)
- **Core Models**: 
  - NewsArticle: Stores collected news with metadata, tracking, and Telegram delivery status
  - SystemStatus: Monitors component health and job execution
  - TelegramMessage: Tracks message delivery attempts and failures
- **Performance Optimization**: Implements strategic database indexes on frequently queried columns (source, published_at, telegram_sent, URL)

## News Collection System
- **RSS Feed Processing**: Uses feedparser library to extract content from cybersecurity news sources
- **Rate Limiting**: Implements decorator-based rate limiting to respect source server limits
- **Duplicate Prevention**: Uses URL-based uniqueness constraints to prevent duplicate article storage
- **Content Processing**: Cleans and normalizes text content, removes HTML tags, and handles encoding issues

## Distribution System
- **Telegram Bot Integration**: Sends formatted news updates to configured Telegram channels/chats
- **Retry Logic**: Implements exponential backoff for failed message deliveries
- **Message Formatting**: Converts articles to HTML-formatted Telegram messages with proper truncation
- **Rate Limiting**: Respects Telegram's API rate limits (20 messages per minute)

## Scheduling Architecture
- **Background Jobs**: Automated collection every 15 minutes, Telegram sending every 2 minutes
- **Cleanup Tasks**: Periodic database maintenance and old data removal
- **Monitoring**: Job execution tracking with error logging and status reporting

## Web Interface
- **Bootstrap-based Dashboard**: Provides real-time system status, statistics, and article management
- **Manual Controls**: Allows triggering of collection and distribution tasks outside scheduled intervals
- **Error Reporting**: Displays system health and failed operations for troubleshooting

# External Dependencies

## Core Infrastructure
- **Flask Ecosystem**: Flask, Flask-SQLAlchemy for web framework and ORM
- **APScheduler**: Background job scheduling and management
- **SQLAlchemy**: Database ORM with PostgreSQL and SQLite support

## Data Sources
- **RSS Feeds**: Multiple cybersecurity news sources (ThreatPost, KrebsOnSecurity, Dark Reading, Bleeping Computer, Security Week, The Hacker News)
- **feedparser**: RSS/Atom feed parsing library
- **requests**: HTTP client for feed collection and API calls

## Distribution Platform
- **Telegram Bot API**: Official Telegram API for message distribution
- **Message Formatting**: HTML parsing and formatting for rich message presentation

## Development and Deployment
- **Werkzeug**: WSGI utilities and development server
- **ProxyFix**: Middleware for proper handling behind reverse proxies
- **Environment Variables**: Configuration management for tokens, database URLs, and chat IDs

## Optional Integrations
- **Database**: Supports both SQLite (local development) and PostgreSQL (production deployment)
- **Logging**: File and console logging with configurable levels
- **Session Management**: Flask session handling with configurable secret keys