# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Start the development server
python run.py

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Architecture Overview

AutoModerate is a Flask-based content moderation platform with the following structure:

### Core Components

- **Flask App Factory**: `app/__init__.py` creates the app with all extensions (SQLAlchemy, Flask-Login, SocketIO)
- **Configuration**: `config/config.py` handles environment-based config (development/production)
- **Entry Point**: `run.py` starts the SocketIO server on port 6217

### Key Modules

- **Models** (`app/models/`): SQLAlchemy models for User, Project, Content, ModerationRule, ModerationResult, APIKey
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
    - `rule_processor.py`: Rule evaluation logic (keyword, regex, AI)
    - `rule_cache.py`: Rule caching and management (5-min TTL)
    - `websocket_notifier.py`: Real-time WebSocket update handling
  - **AI** (`ai/`): OpenAI integration and AI services
    - `ai_moderator.py`: AI moderation strategies and workflows
    - `openai_client.py`: OpenAI client management and connection pooling
    - `result_cache.py`: AI result caching for performance (1-hour TTL)
  - `moderation_service.py`: DEPRECATED - backward compatibility wrapper
  - `openai_service.py`: DEPRECATED - backward compatibility wrapper
- **Templates/Static**: Jinja2 templates and assets for web interface

### Database Design

- **User**: Platform users with authentication
- **Project**: Containers for moderation configurations (users can have multiple projects)
- **APIKey**: Per-project API authentication tokens
- **Content**: Submitted content with moderation status
- **ModerationRule**: Custom rules (keyword, regex, AI prompt-based)
- **ModerationResult**: Moderation decisions and metadata

### Key Integrations

- **OpenAI**: Content moderation via OpenAI's moderation API and GPT models
- **WebSockets**: Real-time updates using Flask-SocketIO
- **SQLite**: Default database (configurable to PostgreSQL/MySQL)

## Development Workflow

1. **Database**: Auto-creates tables and default admin user on startup
2. **Authentication**: Session-based for web, API key for REST endpoints
3. **Real-time Updates**: WebSocket rooms per project for live moderation results
4. **Content Processing**: Clean modular architecture with organized workflow:
   - `ModerationOrchestrator` coordinates the entire process
   - **Moderation module**: `RuleProcessor` + `RuleCache` + `WebSocketNotifier`
   - **AI module**: `AIModerator` + `OpenAIClient` + `ResultCache`
   - Parallel processing with optimized caching at each layer

## Refactored Architecture (New)

The services have been refactored into clean, organized modules:

### Folder Structure:
```
app/services/
├── moderation_orchestrator.py     # Main coordinator
├── moderation/                    # Core moderation logic
│   ├── rule_processor.py         # Rule evaluation (keyword/regex/AI)
│   ├── rule_cache.py             # Rule caching (5min TTL)
│   └── websocket_notifier.py     # Real-time updates
├── ai/                           # AI and OpenAI integration
│   ├── ai_moderator.py           # AI moderation strategies
│   ├── openai_client.py          # Client management & pooling
│   └── result_cache.py           # Result caching (1hr TTL)
├── moderation_service.py         # DEPRECATED wrapper
└── openai_service.py             # DEPRECATED wrapper
```

### Key Benefits:
- **Organized by domain**: Moderation vs AI concerns are separated
- **Single responsibility**: Each file has one clear purpose
- **Better testability**: Smaller, focused components
- **Maintainable**: Changes are localized and easier to understand

### Migration Notes:
- Old `ModerationService` and `OpenAIService` are now deprecated wrappers
- Use `ModerationOrchestrator` instead of `ModerationService` for new code
- Use `AIModerator` instead of `OpenAIService` for new code

## Important Notes

- Server runs on port 6217 by default
- Default admin credentials: admin@example.com / admin123
- Requires OPENAI_API_KEY environment variable for AI moderation
- WebSocket CORS is configured for all origins
- Database migrations handled by SQLAlchemy's create_all()