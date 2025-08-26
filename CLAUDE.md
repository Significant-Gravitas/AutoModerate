# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Quick Start

### Development Setup

```bash
# Environment setup
python -m venv venv
venv\Scripts\activate              # Windows
source venv/bin/activate           # Linux/macOS
pip install -r requirements.txt

# Configuration
# Create .env file and add your OPENAI_API_KEY

# Start development server (port 6217)
python run.py
```

**Access Points:**
- Web Interface: http://localhost:6217
- Default Login: admin@example.com / admin123
- API Documentation: http://localhost:6217/api/docs

### Testing & Code Quality

```bash
# Code formatting and quality
pre-commit install                   # setup hooks
pre-commit run --all-files          # run all checks
autopep8 --in-place --recursive .   # format code
isort .                             # sort imports
```

---

## Architecture Overview

AutoModerate is a Flask-based content moderation platform with OpenAI integration and real-time WebSocket updates.

### Core Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Flask 2.3.3 + Flask-SocketIO | Web framework with real-time capabilities |
| **Database** | SQLAlchemy (SQLite dev, PostgreSQL prod) | ORM with connection pooling |
| **AI Integration** | OpenAI API (GPT models) | Content analysis and moderation |
| **Authentication** | Flask-Login + API Keys | Session-based web auth + API authentication |
| **Real-time** | WebSocket (Flask-SocketIO) | Live moderation result updates |
| **Caching** | In-memory caches | Rule caching + AI result caching |

### Application Structure

```
AutoModerate/
├── run.py                      # Application entry point (port 6217)
├── config/
│   ├── config.py               # Environment-based configuration
│   └── default_rules.py        # Default moderation rules
├── app/
│   ├── __init__.py             # Flask app factory with database initialization
│   ├── models/                 # SQLAlchemy database models
│   │   ├── user.py             # User authentication and management
│   │   ├── project.py          # Projects with member management
│   │   ├── api_key.py          # API authentication tokens
│   │   ├── api_user.py         # API user tracking
│   │   ├── content.py          # Content submissions for moderation
│   │   ├── moderation_rule.py  # Custom moderation rules
│   │   └── moderation_result.py# Moderation decisions and metadata
│   ├── routes/                 # Blueprint-based routing
│   │   ├── auth.py             # Authentication (login/register/profile)
│   │   ├── dashboard.py        # Web interface for project management
│   │   ├── api.py              # RESTful API for content moderation
│   │   ├── websocket.py        # Real-time WebSocket endpoints
│   │   ├── admin.py            # Admin interface for system management
│   │   └── manual_review.py    # Human review interface
│   ├── services/               # Business logic layer
│   │   ├── moderation_orchestrator.py  # Main workflow coordinator
│   │   ├── database_service.py         # Centralized database operations
│   │   ├── ai/                         # OpenAI integration services
│   │   │   ├── ai_moderator.py         # AI moderation strategies with chunking
│   │   │   ├── openai_client.py        # OpenAI client management
│   │   │   └── result_cache.py         # AI result caching
│   │   └── moderation/                 # Core moderation logic
│   │       ├── rule_processor.py       # Rule evaluation (keyword/regex/AI)
│   │       ├── rule_cache.py           # Rule caching
│   │       └── websocket_notifier.py   # Real-time update handling
│   ├── templates/              # Jinja2 templates for web interface
│   ├── static/                 # CSS, JS assets (modular structure)
│   └── utils/                  # Utility functions
└── docker/                     # Docker deployment configuration
```

---

## Database Architecture

### Core Models & Relationships

| Model | Purpose | Key Features |
|-------|---------|--------------|
| **User** | Authentication & management | UUID primary keys, password hashing, admin roles |
| **Project** | Moderation workspaces | Multi-member support, role-based access (owner/admin/member) |
| **ProjectMember** | Project membership | User-project relationships with roles |
| **ProjectInvitation** | Project invites | Token-based invitation system |
| **APIKey** | API authentication | Auto-generated keys (`am_` prefix), usage tracking |
| **APIUser** | API user tracking | External user ID mapping, usage statistics |
| **Content** | Submitted content | JSON metadata, status tracking, API user association |
| **ModerationRule** | Custom rules | Priority-based, multiple types (keyword/regex/AI prompt) |
| **ModerationResult** | Moderation decisions | Confidence scores, processing metrics, detailed metadata |

### Key Relationships

- User -> Projects (1:N ownership)
- User <-> Projects (N:M membership via ProjectMember)
- Project -> APIKeys, Content, ModerationRules (1:N)
- Content -> ModerationResults (1:N)
- APIUser -> Content (1:N)

### Advanced Features

- Multi-tenancy: Project-based isolation with member management
- Usage Tracking: API usage statistics per key and user  
- Rich Metadata: JSON fields for flexible data storage
- Connection Pooling: Optimized database performance (dev: 3-5, prod: 10-20 connections)

---

## Content Moderation Pipeline

### Processing Workflow

1. **Content Submitted** - API receives content via POST /api/moderate
2. **Token Count Analysis** - Content size analyzed for chunking decisions
3. **Rule Processing** - Rules processed by priority and type:
   - Fast rules (keyword/regex) processed first for early exit
   - AI rules processed in parallel if no fast rule matches
4. **Decision Making** - Final decision based on rule matches
5. **Manual Review Check** - Low confidence results flagged for human review
6. **Database Save** - Results stored and WebSocket updates sent

### AI Moderation Strategies

1. **Custom Prompt Analysis**: Rule-specific AI evaluation using custom prompts
2. **Smart Chunking**: Automatic content splitting at sentence boundaries for large content
3. **Token Management**: Dynamic content chunking based on model context windows

### Performance Optimizations

- **Parallel Processing**: AI rules processed concurrently with early exit
- **Multi-level Caching**: Rule cache + AI result cache
- **Bulk Operations**: Efficient database writes for moderation results
- **Priority-based**: Fast rules (keyword/regex) processed first

---

## Configuration & Environment

### Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `OPENAI_API_KEY` | **Required** - OpenAI API access | - | `sk-...` |
| `OPENAI_CHAT_MODEL` | GPT model for analysis | `gpt-5-nano-2025-08-07` | `gpt-4` |
| `OPENAI_CONTEXT_WINDOW` | Model context window size | `400000` | `128000` |
| `OPENAI_MAX_OUTPUT_TOKENS` | Maximum output tokens | `128000` | `4096` |
| `DATABASE_URL` | Database connection | SQLite local | `postgresql://...` |
| `FLASK_CONFIG` | Environment mode | `default` | `production` |
| `SECRET_KEY` | Flask session security | Auto-generated | `your-secret-key` |
| `ADMIN_EMAIL` | Default admin email | `admin@example.com` | - |
| `ADMIN_PASSWORD` | Default admin password | `admin123` | - |
| `SQL_DEBUG` | Enable SQL query logging | `False` | `True` |

### Database Connection Pooling

```python
# Development Configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 3,           # Base connections
    'max_overflow': 5,        # Additional connections
    'pool_timeout': 20,       # Connection wait time
    'pool_recycle': 1800,     # Connection lifetime (30min)
    'pool_pre_ping': True,    # Connection health checks
    'echo': False             # SQL query logging
}

# Production Configuration  
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
    'pool_pre_ping': True,
    'echo': False
}
```

---

## API Reference

### Authentication

All API requests require an API key in the header:
```bash
X-API-Key: am_your-api-key-here
```

### Content Moderation Endpoint

**POST** `/api/moderate`

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: am_your-api-key" \
  -d '{
    "type": "text",
    "content": "Content to moderate",
    "metadata": {
      "source": "user_comment",
      "user_id": "external_user_123"
    }
  }' \
  http://localhost:6217/api/moderate
```

**Response Format:**
```json
{
  "success": true,
  "content_id": "uuid-here",
  "status": "approved|rejected|flagged",
  "moderation_results": [
    {
      "decision": "approved",
      "confidence": 0.95,
      "reason": "Content passed all moderation checks",
      "moderator_type": "rule|ai|manual",
      "processing_time": 0.23
    }
  ]
}
```

### Additional Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| `GET` | `/api/content/<id>` | Get specific content details | - |
| `GET` | `/api/content` | List content with pagination | `page`, `per_page`, `status` |
| `GET` | `/api/stats` | Get project statistics | - |
| `GET` | `/api/health` | Service health check | - |
| `GET` | `/api/docs` | API documentation | - |

---

## Deployment

### Docker Deployment

```bash
# Using Docker Compose (includes PostgreSQL)
cd docker/
docker-compose up -d

# Custom environment variables
OPENAI_API_KEY=sk-your-key docker-compose up -d
```

**Docker Configuration:**
- Base Image: `python:3.11-slim`  
- Port: `6217`
- Database: PostgreSQL 15 Alpine
- Volumes: Persistent data storage
- Health Checks: Built-in service monitoring

### Production Considerations

1. Security: Set secure `SECRET_KEY`, enable HTTPS
2. Database: Use PostgreSQL with connection pooling
3. Web Server: Deploy with Gunicorn + Nginx
4. Monitoring: Implement logging and health checks
5. API Keys: Rotate keys regularly, monitor usage

---

## Development Notes

### Key Implementation Details

- **Async Architecture**: Routes use `async def` with database service layer
- **App Factory Pattern**: `create_app()` with blueprint registration
- **Retry Logic**: Database initialization with exponential backoff  
- **Custom Filters**: Jinja2 `to_dict_list` filter for template data conversion
- **Early Exit**: Moderation stops at first matching rule for performance
- **WebSocket Rooms**: Project-based real-time update isolation

### Important Architectural Decisions

- **Windows Compatibility**: Use `venv\Scripts\activate` for Windows
- **Token Management**: Dynamic chunking based on model context windows
- **Manual Review Flagging**: Low confidence results automatically flagged for human review
- **Database Service Layer**: Centralized async database operations for consistency
- **Connection Pooling**: Configurable pool sizes for different environments

### Moderation Rule Types

| Type | Processing Speed | Use Case | Configuration |
|------|-----------------|----------|---------------|
| **Keyword** | Fast | Simple word blocking | `keywords` list, `case_sensitive` |
| **Regex** | Fast | Pattern matching | `pattern`, `flags` (i/m/s) |
| **AI Prompt** | Slow | Custom AI analysis | Custom `prompt` text |

---

## System Monitoring

### Cache Statistics
- Rule Cache: Hit/miss ratios, cache size, TTL tracking
- AI Result Cache: API call reduction metrics, cache effectiveness
- Request Cache: Per-request cache performance summaries

### Performance Metrics
- Processing Times: Rule evaluation, AI analysis, total request time
- Database Stats: Connection pool usage, query performance
- API Usage: Request counts, rate limiting, error rates

---

*This documentation is maintained for Claude Code. For current API examples and deployment guides, refer to inline code comments.*