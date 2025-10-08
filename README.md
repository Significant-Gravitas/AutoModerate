# AutoModerate - Content Moderation Platform

A comprehensive Flask-based content moderation platform that leverages OpenAI for intelligent content analysis with real-time WebSocket updates and multi-tenant project management.

## Key Features

- **Multi-Tenant Project Management**: Project-based organization with member management and role-based access
- **Intelligent Moderation Pipeline**: Keyword, regex, and AI-powered content analysis with parallel processing
- **OpenAI Integration**: Advanced GPT models with smart chunking and result caching for optimal performance
- **Real-time Updates**: WebSocket-powered live notifications for moderation results
- **Comprehensive API**: RESTful API with authentication, pagination, and detailed analytics
- **Performance Optimized**: Connection pooling, caching layers, and early-exit processing
- **Manual Review System**: Low-confidence results automatically flagged for human review

## Quick Start

<details>
<summary>Installation & Setup</summary>

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup Steps

```bash
# Clone and setup environment
git clone https://github.com/Bentlybro/AutoModerate
cd AutoModerate
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start development server
python run.py
```

**Access Points:**
- Web Interface: http://localhost:6217
- Default Login: admin@example.com / admin123
- API Documentation: http://localhost:6217/api/docs

</details>

## Architecture

<details>
<summary>System Architecture & Technology Stack</summary>

### Core Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Flask 2.3.3 + Flask-SocketIO | Web framework with real-time capabilities |
| **Database** | SQLAlchemy (SQLite dev, PostgreSQL prod) | ORM with connection pooling |
| **AI Integration** | OpenAI API (GPT models) | Content analysis and moderation |
| **Authentication** | Flask-Login + API Keys | Session-based web auth + API authentication |
| **Real-time** | WebSocket (Flask-SocketIO) | Live moderation result updates |
| **Caching** | Multi-layer caching | Rule caching + AI result caching |

### Application Structure

```
AutoModerate/
├── run.py                      # Application entry point (port 6217)
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
├── README.md                   # Main documentation
├── CLAUDE.md                   # Claude Code project instructions
│
├── config/                     # Configuration files
│   ├── config.py               # Environment-based configuration
│   └── default_rules.py        # Default moderation rules
│
├── app/                        # Main application directory
│   ├── __init__.py             # Flask app factory with database initialization
│   │
│   ├── models/                 # SQLAlchemy database models
│   │   ├── __init__.py         # Models package initialization
│   │   ├── user.py             # User authentication and management
│   │   ├── project.py          # Projects with member management
│   │   ├── api_key.py          # API authentication tokens
│   │   ├── api_user.py         # API user tracking
│   │   ├── content.py          # Content submissions for moderation
│   │   ├── moderation_rule.py  # Custom moderation rules
│   │   ├── moderation_result.py# Moderation decisions and metadata
│   │   └── system_settings.py  # System-wide configuration settings
│   │
│   ├── routes/                 # Blueprint-based routing
│   │   ├── __init__.py         # Routes package initialization
│   │   ├── auth.py             # Authentication (login/register/profile)
│   │   ├── dashboard.py        # Web interface for project management
│   │   ├── api.py              # RESTful API for content moderation
│   │   ├── websocket.py        # Real-time WebSocket endpoints
│   │   ├── admin.py            # Admin interface for system management
│   │   ├── manual_review.py    # Human review interface
│   │   └── monitoring.py       # System monitoring and health checks
│   │
│   ├── services/               # Business logic layer
│   │   ├── __init__.py         # Services package initialization
│   │   ├── moderation_orchestrator.py  # Main workflow coordinator
│   │   ├── database_service.py         # Centralized database operations
│   │   ├── error_tracker.py            # Error tracking and logging
│   │   │
│   │   ├── ai/                         # OpenAI integration services
│   │   │   ├── __init__.py             # AI services initialization
│   │   │   ├── ai_moderator.py         # AI moderation strategies with chunking
│   │   │   ├── openai_client.py        # OpenAI client management
│   │   │   └── result_cache.py         # AI result caching
│   │   │
│   │   ├── moderation/                 # Core moderation logic
│   │   │   ├── __init__.py             # Moderation services initialization
│   │   │   ├── rule_processor.py       # Rule evaluation (keyword/regex/AI)
│   │   │   └── websocket_notifier.py   # Real-time update handling
│   │   │
│   │   └── notifications/              # Notification services
│   │       ├── __init__.py             # Notifications initialization
│   │       └── discord_notifier.py     # Discord webhook notifications
│   │
│   ├── schemas/                # Request/Response schemas
│   │   ├── __init__.py         # Schemas package initialization
│   │   └── api_schemas.py      # API validation schemas
│   │
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py         # Utils package initialization
│   │   ├── error_handlers.py   # Error handling utilities
│   │   └── project_access.py   # Project access control helpers
│   │
│   ├── templates/              # Jinja2 templates for web interface
│   │   ├── base.html           # Base template with common layout
│   │   │
│   │   ├── auth/               # Authentication templates
│   │   │   ├── login.html      # Login page
│   │   │   ├── register.html   # Registration page
│   │   │   └── profile.html    # User profile page
│   │   │
│   │   ├── dashboard/          # Dashboard templates
│   │   │   ├── index.html      # Dashboard home
│   │   │   ├── projects.html   # Projects list
│   │   │   ├── project_detail.html     # Project overview
│   │   │   ├── project_settings.html   # Project configuration
│   │   │   ├── project_analytics.html  # Project statistics
│   │   │   ├── create_project.html     # New project form
│   │   │   ├── api_keys.html   # API keys management
│   │   │   ├── rules.html      # Rules list
│   │   │   ├── create_rule.html# Rule creation form
│   │   │   ├── content.html    # Content moderation history
│   │   │   └── members.html    # Project members management
│   │   │
│   │   ├── admin/              # Admin templates
│   │   │   ├── index.html      # Admin dashboard
│   │   │   ├── users.html      # User management
│   │   │   ├── user_detail.html# User details
│   │   │   ├── projects.html   # All projects overview
│   │   │   ├── analytics.html  # System analytics
│   │   │   └── system_health.html  # System health monitoring
│   │   │
│   │   ├── manual_review/      # Manual review templates
│   │   │   ├── index.html      # Review queue
│   │   │   ├── review_content.html    # Content review interface
│   │   │   ├── api_users.html  # API users list
│   │   │   └── api_user_detail.html   # API user statistics
│   │   │
│   │   └── api/                # API documentation templates
│   │       └── docs.html       # Interactive API documentation
│   │
│   └── static/                 # Static assets (CSS, JS)
│       ├── css/                # Stylesheets
│       │   ├── core/           # Core styles
│       │   │   ├── layout.css  # Base layout styles
│       │   │   └── dark-mode.css   # Dark mode theme
│       │   ├── components/     # Reusable components
│       │   │   ├── forms.css   # Form styles
│       │   │   ├── modals.css  # Modal dialog styles
│       │   │   └── tables.css  # Table styles
│       │   ├── dashboard/      # Dashboard-specific styles
│       │   │   ├── project_detail.css  # Project detail page
│       │   │   └── rules.css   # Rules page styles
│       │   ├── api/            # API documentation styles
│       │   │   └── docs.css    # API docs styling
│       │   └── utilities/      # Utility styles
│       │       └── responsive.css  # Responsive design utilities
│       │
│       └── js/                 # JavaScript files
│           ├── base.js         # Global JavaScript utilities
│           ├── auth/           # Authentication scripts
│           │   └── profile.js  # Profile page functionality
│           ├── dashboard/      # Dashboard scripts
│           │   ├── project_detail.js   # Project detail page
│           │   ├── project_settings.js # Project settings
│           │   ├── api_keys.js         # API key management
│           │   ├── rules.js            # Rules management
│           │   ├── create_rule.js      # Rule creation form
│           │   ├── content.js          # Content viewing
│           │   └── members.js          # Member management
│           └── api/            # API documentation scripts
│               └── docs.js     # Interactive API testing
│
├── tests/                      # Test suite
│   └── e2e_test.py             # End-to-end integration tests
│
├── docs/                       # Additional documentation
│   ├── README.md               # Documentation index
│   ├── api/                    # API documentation
│   │   ├── overview.md         # API overview
│   │   ├── moderation.md       # Moderation endpoints
│   │   ├── statistics.md       # Statistics endpoints
│   │   └── websockets.md       # WebSocket documentation
│   └── guides/                 # Implementation guides
│       ├── installation.md     # Installation guide
│       └── architecture.md     # Architecture details
│
├── docker/                     # Docker development setup
│   ├── Dockerfile              # Development Docker image
│   ├── docker-compose.yml      # Docker Compose configuration
│   ├── .env.docker.example     # Docker environment template
│   └── README.md               # Docker deployment guide
│
└── deploy/                     # Production deployment
    ├── Dockerfile              # Production Docker image
    ├── cloudbuild.yaml         # Google Cloud Build configuration
    └── README.md               # Deployment documentation
```

### Content Moderation Pipeline

```mermaid
flowchart TD
    A[Client Application] -->|POST /api/moderate<br/>content + metadata| B[AutoModerate API]
    B --> C[Validate API Key<br/>& Extract Project]
    C --> D[Store Content in Database]
    D --> E[Token Analysis &<br/>Chunking Decision]
    E --> F{Rule Processing}

    F --> G[Fast Rules<br/>Keyword/Regex]
    G --> H{Match Found?}
    H -->|Yes| M[Generate Decision]
    H -->|No| I[AI Rules<br/>Parallel Processing]

    I --> J[OpenAI API Call #1<br/>w/ caching]
    I --> K[OpenAI API Call #2<br/>w/ caching]
    J --> L{First Match or<br/>All Processed}
    K --> L
    L --> M

    M --> N{Low Confidence?<br/>< 0.3}
    N -->|Yes| O[Flag for Manual Review]
    N -->|No| P[Final Decision<br/>approve/reject/flag]
    O --> Q[Save Result to DB<br/>+ WebSocket Notify]
    P --> Q
    Q --> R[Return Response to Client]

    style A fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style B fill:#F5A623,stroke:#C47F1A,stroke-width:2px,color:#fff
    style C fill:#7B68EE,stroke:#5A4DB5,stroke-width:2px,color:#fff
    style D fill:#00BFA5,stroke:#008C7A,stroke-width:2px,color:#fff
    style E fill:#9013FE,stroke:#6B0FBF,stroke-width:2px,color:#fff
    style G fill:#FF6B6B,stroke:#CC5555,stroke-width:2px,color:#fff
    style H fill:#FF8C00,stroke:#CC7000,stroke-width:2px,color:#fff
    style I fill:#E91E63,stroke:#B71850,stroke-width:2px,color:#fff
    style J fill:#EC407A,stroke:#BD3361,stroke-width:2px,color:#fff
    style K fill:#EC407A,stroke:#BD3361,stroke-width:2px,color:#fff
    style L fill:#F06292,stroke:#C04F75,stroke-width:2px,color:#fff
    style M fill:#4CAF50,stroke:#3D8B40,stroke-width:2px,color:#fff
    style N fill:#FF9800,stroke:#CC7A00,stroke-width:2px,color:#fff
    style O fill:#F57C00,stroke:#C46300,stroke-width:2px,color:#fff
    style P fill:#8BC34A,stroke:#6F9C3B,stroke-width:2px,color:#000
    style Q fill:#9C27B0,stroke:#7D1F8D,stroke-width:2px,color:#fff
    style R fill:#2196F3,stroke:#1A78C2,stroke-width:2px,color:#fff
```

**Processing Flow:**

1. **Content Submission** - API receives content via POST /api/moderate
2. **Token Analysis** - Content size analyzed for chunking decisions
3. **Rule Processing** - Priority-based rule evaluation:
   - Fast rules (keyword/regex) processed first for early exit
   - AI rules processed in parallel with ThreadPoolExecutor
4. **Decision Making** - First matching rule determines outcome
5. **Manual Review** - Low confidence results automatically flagged
6. **Database Save** - Results stored with WebSocket notifications

</details>

## API Usage

<details>
<summary>API Reference & Examples</summary>

### Authentication

All API requests require an API key in the header:

```bash
X-API-Key: am_your-api-key-here
```

### Content Moderation

**Submit Content for Moderation**

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

</details>

## Moderation Rules

<details>
<summary>Rule Types & Configuration</summary>

### Rule Types

| Type | Processing Speed | Use Case | Configuration |
|------|-----------------|----------|---------------|
| **Keyword** | Fast | Simple word blocking | `keywords` list, `case_sensitive` |
| **Regex** | Fast | Pattern matching | `pattern`, `flags` (i/m/s) |
| **AI Prompt** | Slow | Custom AI analysis | Custom `prompt` text |

### Rule Processing

- **Priority-based**: Rules processed in order of priority
- **Early Exit**: Processing stops at first matching rule
- **Parallel AI**: AI rules processed concurrently for optimal performance
- **Manual Review**: Low confidence results (<0.3) automatically flagged

### Creating Rules

1. Navigate to your project dashboard
2. Select "Moderation Rules"
3. Click "Create Rule"
4. Configure rule type and parameters
5. Set priority (lower numbers = higher priority)
6. Choose action: approve, reject, or flag for manual review

</details>

## Configuration

<details>
<summary>Environment Variables & Settings</summary>

### Required Environment Variables

```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-openai-api-key

# Optional OpenAI Settings
OPENAI_CHAT_MODEL=gpt-5-nano-2025-08-07  # Default model
OPENAI_CONTEXT_WINDOW=400000              # Model context window
OPENAI_MAX_OUTPUT_TOKENS=128000           # Maximum output tokens

# Database Configuration
DATABASE_URL=sqlite:///automoderate.db    # SQLite for dev
# DATABASE_URL=postgresql://user:pass@host/db  # PostgreSQL for prod

# Flask Configuration
FLASK_CONFIG=default                      # Environment mode
SECRET_KEY=auto-generated                 # Session security
ADMIN_EMAIL=admin@example.com            # Default admin
ADMIN_PASSWORD=admin123                   # Default password

# Debug Settings
SQL_DEBUG=False                          # Enable SQL query logging
```

### Database Connection Pooling

**Development Configuration:**
- Pool Size: 3 base connections
- Max Overflow: 5 additional connections
- Connection Timeout: 20 seconds
- Connection Lifetime: 30 minutes

**Production Configuration:**
- Pool Size: 10 base connections
- Max Overflow: 20 additional connections
- Connection Timeout: 30 seconds
- Health Checks: Enabled

</details>

## Performance & Optimization

<details>
<summary>Performance Features</summary>

### AI Processing Optimizations

- **Parallel Processing**: AI rules processed concurrently with ThreadPoolExecutor
- **Early Exit**: Processing stops at first rule match
- **Smart Chunking**: Large content automatically split at sentence boundaries
- **Result Caching**: AI results cached to reduce duplicate API calls
- **Connection Pooling**: Optimized HTTP client with 200 keepalive connections

### Processing Times

- **Fast Rules** (keyword/regex): ~50-200ms
- **AI Rules**: ~5-10 seconds (OpenAI API dependent)
- **Cache Hits**: ~50-100ms
- **Parallel AI Rules**: Multiple rules processed simultaneously

### Caching Layers

1. **Rule Cache**: Project rules cached in memory with TTL
2. **AI Result Cache**: OpenAI responses cached by content hash
3. **Connection Pool**: HTTP connections reused for multiple requests

</details>

## Testing & Quality

<details>
<summary>Code Quality & Testing</summary>

### Code Quality Tools

```bash
# Setup pre-commit hooks
pre-commit install

# Manual code formatting
autopep8 --in-place --recursive .
isort .

# Run all quality checks
pre-commit run --all-files
```

**Pre-commit hooks automatically run:**
- autopep8 with max line length 127
- isort with black profile
- flake8 code quality checks
- trailing whitespace removal

### End-to-End Testing

```bash
# Run E2E test suite
python -m pytest tests/e2e_test.py -v
```

**E2E tests cover:**
- User registration and authentication
- Project creation and management
- API key generation and usage
- Content moderation pipeline
- Rule creation and processing
- WebSocket real-time updates

</details>

## Deployment

<details>
<summary>Production Deployment</summary>

### Docker Deployment

```bash
# Using Docker Compose (includes PostgreSQL)
cd docker/
docker-compose up -d

# Custom environment variables
OPENAI_API_KEY=sk-your-key docker-compose up -d
```

**Docker Configuration:**
- Base Image: python:3.11-slim
- Port: 6217
- Database: PostgreSQL 15 Alpine
- Volumes: Persistent data storage
- Health Checks: Built-in service monitoring

### Production Considerations

1. **Security**: Set secure SECRET_KEY, enable HTTPS
2. **Database**: Use PostgreSQL with connection pooling
3. **Web Server**: Deploy with Gunicorn + Nginx
4. **Monitoring**: Implement logging and health checks
5. **API Keys**: Rotate keys regularly, monitor usage
6. **SSL/TLS**: Enable HTTPS for secure API communication

### Environment-Specific Configs

**Development:**
- SQLite database
- Debug logging enabled
- Hot reload
- Smaller connection pools

**Production:**
- PostgreSQL database
- Optimized connection pools
- Error logging only
- Security headers enabled

</details>

## Database Schema

<details>
<summary>Database Models & Relationships</summary>

### Core Models

| Model | Purpose | Key Features |
|-------|---------|--------------|
| **User** | Authentication & management | UUID primary keys, password hashing, admin roles |
| **Project** | Moderation workspaces | Multi-member support, role-based access |
| **ProjectMember** | Project membership | User-project relationships with roles |
| **ProjectInvitation** | Project invites | Token-based invitation system |
| **APIKey** | API authentication | Auto-generated keys (am_ prefix), usage tracking |
| **APIUser** | API user tracking | External user ID mapping, usage statistics |
| **Content** | Submitted content | JSON metadata, status tracking |
| **ModerationRule** | Custom rules | Priority-based, multiple types |
| **ModerationResult** | Moderation decisions | Confidence scores, processing metrics |

### Key Relationships

**Detailed Relationships:**
- **User → Project**: 1:N ownership (creator)
- **User ↔ Project**: N:M membership via ProjectMember (owner/admin/member roles)
- **Project → APIKey**: 1:N (multiple keys per project)
- **Project → Content**: 1:N (all content submissions)
- **Project → ModerationRule**: 1:N (custom rules per project)
- **Project → ProjectInvitation**: 1:N (pending invitations)
- **Content → ModerationResult**: 1:N (multiple moderation checks)
- **APIUser → Content**: 1:N (tracks external user submissions)

### Advanced Features

- **Multi-tenancy**: Project-based isolation with member management
- **Usage Tracking**: API usage statistics per key and user
- **Rich Metadata**: JSON fields for flexible data storage
- **Audit Trail**: Comprehensive logging of all moderation decisions

</details>

## Contributing

<details>
<summary>Development Guidelines</summary>

### Getting Started

1. Fork the repository
2. Create a feature branch
3. Setup development environment
4. Make your changes following the coding standards
5. Add tests for new functionality
6. Run the test suite
7. Submit a pull request

### Coding Standards

- **Python**: PEP 8 compliance with max line length 127
- **Imports**: Organized with isort (black profile)
- **Code Quality**: Flake8 linting required
- **Testing**: E2E tests for new features
- **Documentation**: Update relevant documentation

### Pre-commit Hooks

All commits must pass pre-commit hooks:
- Code formatting (autopep8)
- Import sorting (isort)
- Linting (flake8)
- Trailing whitespace removal

</details>

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the comprehensive documentation
- Review the API examples and test suite