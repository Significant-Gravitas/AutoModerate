# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Start the development server (runs on port 6217)
python run.py

# Access application
# Web interface: http://localhost:6217
# Default login: admin@example.com / admin123
```

## Architecture Overview

AutoModerate is a Flask-based content moderation platform with the following structure:

### Core Components

- **Flask App Factory**: `app/__init__.py` creates the app with all extensions (SQLAlchemy, Flask-Login, SocketIO)
- **Configuration**: `config/config.py` handles environment-based config with database connection pooling
- **Entry Point**: `run.py` starts the SocketIO server on port 6217

### Key Modules

- **Models** (`app/models/`): SQLAlchemy models for User, Project, Content, ModerationRule, ModerationResult, APIKey, APIUser
- **Routes** (`app/routes/`): Blueprint-based routing
  - `auth.py`: Authentication and user management
  - `dashboard.py`: Web interface for project management
  - `api.py`: RESTful API endpoints for content moderation
  - `websocket.py`: Real-time WebSocket communications
  - `admin.py`: Admin interface for system management
  - `manual_review.py`: Human review interface
- **Services** (`app/services/`): Clean modular business logic
  - `moderation_orchestrator.py`: Main coordination and workflow management
  - **Moderation** (`moderation/`): Core moderation logic
    - `rule_processor.py`: Rule evaluation logic (keyword, regex, AI) with parallel processing
    - `rule_cache.py`: Rule caching and management (5-min TTL)
    - `websocket_notifier.py`: Real-time WebSocket update handling
  - **AI** (`ai/`): OpenAI integration and AI services
    - `ai_moderator.py`: AI moderation strategies with chunking for large content
    - `openai_client.py`: OpenAI client management and connection pooling
    - `result_cache.py`: AI result caching for performance (1-hour TTL)
  - `moderation_service.py`: DEPRECATED - backward compatibility wrapper
  - `openai_service.py`: DEPRECATED - backward compatibility wrapper
- **Templates/Static**: Jinja2 templates with custom filters and assets for web interface

### Database Design

- **User**: Platform users with authentication
- **Project**: Containers for moderation configurations (users can have multiple projects)
- **APIKey**: Per-project API authentication tokens
- **APIUser**: API usage tracking and statistics
- **Content**: Submitted content with moderation status
- **ModerationRule**: Custom rules (keyword, regex, AI prompt-based)
- **ModerationResult**: Moderation decisions and metadata with bulk operations

### Key Integrations

- **OpenAI**: Multi-layered content moderation (baseline API + enhanced GPT analysis)
- **WebSockets**: Real-time updates using Flask-SocketIO with CORS enabled
- **Database**: SQLite default, PostgreSQL/MySQL production with connection pooling

## Development Workflow

1. **Database**: Auto-creates tables with retry logic and default admin user on startup
2. **Authentication**: Session-based for web, API key for REST endpoints
3. **Real-time Updates**: WebSocket rooms per project for live moderation results
4. **Content Processing**: Optimized workflow with parallel processing:
   - Fast rules (keyword/regex) processed first for immediate decisions
   - AI rules processed in parallel with early exit on first match
   - Chunked processing for large content (12,000 token limit per chunk)
   - Comprehensive caching at rule and result levels

## Content Moderation Pipeline

### Processing Flow:
1. **Rule Prioritization**: Fast rules (keyword/regex) → AI rules by priority
2. **Parallel AI Processing**: Multiple AI rules evaluated concurrently
3. **Early Exit**: First matching rule terminates processing
4. **Chunked Analysis**: Large content split intelligently at sentence boundaries
5. **Manual Review Flagging**: Low confidence or conflicting results flagged for human review
6. **Real-time Notifications**: WebSocket updates sent asynchronously

### AI Moderation Strategies:
- **Custom Prompt Analysis**: Rule-specific AI evaluation using GPT-3.5-turbo
- **Baseline Safety**: OpenAI's moderation API for standard policy violations
- **Enhanced Safety**: Comprehensive GPT analysis for nuanced content issues
- **Token Management**: Automatic chunking for content exceeding 12,000 tokens

## Caching and Performance

- **Rule Cache**: 5-minute TTL for project rules with automatic invalidation
- **Result Cache**: 1-hour TTL for AI moderation results to reduce API calls
- **Database Pooling**: Configurable connection pools (3-5 dev, 10-20 prod)
- **Bulk Operations**: Efficient database writes for moderation results

## Configuration

### Database Connection Pooling:
```python
# Development
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 3,
    'max_overflow': 5,
    'pool_timeout': 20,
    'pool_recycle': 1800,
    'pool_pre_ping': True
}

# Production  
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
    'pool_pre_ping': True
}
```

### Environment Variables:
- `OPENAI_API_KEY`: Required for AI moderation (from OpenAI dashboard)
- `DATABASE_URL`: Database connection string (defaults to SQLite, auto-detects PostgreSQL)
- `FLASK_CONFIG`: Environment mode (development/production/default)
- `FLASK_ENV`: Flask environment (development/production)
- `SECRET_KEY`: Flask secret key for sessions
- `ADMIN_EMAIL`: Default admin email (default: admin@example.com)  
- `ADMIN_PASSWORD`: Default admin password (default: admin123)
- `SQL_DEBUG`: Enable SQLAlchemy query logging in development

## API Usage

### Content Moderation Endpoint
```bash
# Submit content for moderation
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "text", 
    "content": "Content to moderate",
    "metadata": {"source": "user_comment"}
  }' \
  http://localhost:6217/api/moderate

# Get content status
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/content/content-id

# List content with pagination  
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/content?page=1&per_page=20&status=approved"

# Get statistics
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/stats
```

## Important Notes

- Server runs on port 6217 by default (configured in run.py:23)
- Default admin credentials: admin@example.com / admin123
- WebSocket CORS configured for all origins
- Database initialization includes retry logic for connection pool issues
- Custom Jinja2 filter `to_dict_list` available for template data conversion
- Deprecated services (`moderation_service.py`, `openai_service.py`) maintained for backward compatibility
- No specific test runner configured - project uses standard Flask testing patterns
- Docker configuration available in `docker/` directory for containerized deployment