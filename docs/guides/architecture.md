# System Architecture

AutoModerate is built with a modular, scalable architecture designed for high-performance content moderation with real-time capabilities.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AutoModerate Platform                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Web Client  │    │ API Client  │    │    WebSocket Client     │  │
│  │ Dashboard   │    │Integration  │    │   Real-time Updates     │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│         │                    │                         │            │
│         └────────────────────┼─────────────────────────┘            │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Flask Application                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │   │
│  │  │   Routes    │  │   Models    │  │     Extensions      │   │   │
│  │  │(Blueprints) │  │ (SQLAlchemy)│  │(SocketIO, Login,etc)│   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 Service Layer                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │           ModerationOrchestrator                        │ │   │
│  │  │              (Main Coordinator)                         │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌──────────────────┐              ┌──────────────────────┐  │   │
│  │  │   Moderation     │              │    AI Services       │  │   │
│  │  │   Services       │              │                      │  │   │
│  │  │ ┌──────────────┐ │              │ ┌─────────────────┐  │  │   │
│  │  │ │RuleProcessor │ │              │ │  AIModerator    │  │  │   │
│  │  │ │RuleCache     │ │              │ │  OpenAIClient   │  │  │   │
│  │  │ │WebSocketNotif│ │              │ │  ResultCache    │  │  │   │
│  │  │ └──────────────┘ │              │ └─────────────────┘  │  │   │
│  │  └──────────────────┘              └──────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  Data Layer                                  │   │
│  │  ┌─────────────┐    ┌─────────────────┐    ┌──────────────┐  │   │
│  │  │  Database   │    │   OpenAI API    │    │    Cache     │  │   │
│  │  │(PostgreSQL/ │    │                 │    │  (In-Memory) │  │   │
│  │  │  SQLite)    │    │                 │    │              │  │   │
│  │  └─────────────┘    └─────────────────┘    └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Web Application Layer

#### Flask Application Factory
- **Location**: `app/__init__.py`
- **Purpose**: Creates and configures the Flask application
- **Features**:
  - Blueprint registration
  - Extension initialization
  - Database setup
  - Default admin user creation

#### Blueprints (Routes)
- **auth.py**: User authentication and session management
- **dashboard.py**: Web interface for project management
- **api.py**: RESTful API endpoints
- **websocket.py**: WebSocket event handlers
- **admin.py**: Administrative interface
- **manual_review.py**: Human review workflows

### 2. Service Layer

#### ModerationOrchestrator
- **Location**: `app/services/moderation_orchestrator.py`
- **Purpose**: Main coordinator for content moderation workflow
- **Responsibilities**:
  - Coordinates between all service modules
  - Handles workflow logic (fast rules → AI rules → fallbacks)
  - Manages database operations
  - Triggers WebSocket notifications
  - Provides statistics and monitoring

#### Moderation Services
Located in `app/services/moderation/`:

**RuleProcessor**
- Evaluates different rule types (keyword, regex, AI)
- Handles parallel AI rule processing
- Provides early termination for performance

**RuleCache**
- Manages rule caching with 5-minute TTL
- Reduces database queries
- Provides cache statistics

**WebSocketNotifier**
- Handles real-time notifications
- Manages project-specific rooms
- Provides event broadcasting

#### AI Services
Located in `app/services/ai/`:

**AIModerator**
- Multiple AI moderation strategies
- Custom prompt analysis
- Baseline safety checking
- Enhanced default moderation

**OpenAIClient**
- Connection pooling and management
- HTTP/2 optimization
- Error handling and retries

**ResultCache**
- AI result caching with 1-hour TTL
- Performance optimization
- Cache cleanup and monitoring

### 3. Data Models

#### Core Models
- **User**: Platform users with authentication
- **Project**: Containers for moderation configurations
- **APIKey**: Per-project authentication tokens
- **Content**: Submitted content with moderation status
- **ModerationRule**: Custom rules (keyword, regex, AI prompt)
- **ModerationResult**: Moderation decisions and metadata
- **APIUser**: External users tracked for statistics

#### Relationships
```sql
User (1) → (∞) Project
Project (1) → (∞) APIKey
Project (1) → (∞) ModerationRule
Project (1) → (∞) Content
Content (1) → (∞) ModerationResult
Content (∞) → (1) APIUser
```

## Data Flow

### 1. Content Submission Flow

```
API Client
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. API Route (/api/moderate)                                        │
│    • Validate API key                                               │
│    • Create content record                                          │
│    • Extract user information                                       │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. ModerationOrchestrator.moderate_content()                        │
│    • Get cached rules for project                                   │
│    • Separate fast rules (keyword/regex) vs AI rules                │
│    • Start timing                                                   │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. RuleProcessor.process_rules()                                    │
│    • Process fast rules first (sequential, immediate)               │
│    • If match found: return decision                                │
│    • If no match: process AI rules (parallel)                       │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. AI Rule Processing (Parallel)                                    │
│    • ThreadPoolExecutor with up to 10 workers                       │
│    • Each rule calls AIModerator.moderate_content()                 │
│    • Early termination on first match                               │
│    • Cache results for performance                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Decision & Storage                                               │
│    • Determine final decision (approved/rejected/flagged)           │
│    • Save to database (content + moderation results)                │
│    • Update user statistics                                         │
│    • Calculate processing time                                      │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Real-time Notifications                                          │
│    • WebSocketNotifier.send_update_async()                          │
│    • Broadcast to project room                                      │
│    • Include decision, timing, rule info                            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. API Response                                                     │
│    • Return JSON with decision, results, timing                     │
│    • Include content_id for future reference                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Real-time Update Flow

```
Content Moderated
    │
    ▼
WebSocketNotifier
    │
    ▼
SocketIO Emit → Project Room (project_12345)
    │
    ▼
Connected Clients
    │
    ├─ Dashboard Users (Web Interface)
    ├─ API Clients (WebSocket Integration)
    └─ Mobile Apps (Real-time Updates)
```

### 3. Rule Processing Strategy

```
Content Received
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Fast Rules (Sequential)                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐   │
│ │  Keyword    │→ │   Regex     │→ │      If Match Found:        │   │
│ │   Rules     │  │   Rules     │  │     Return Immediately      │   │
│ │  (~0.01s)   │  │  (~0.05s)   │  │                             │   │
│ └─────────────┘  └─────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
    │ (No matches)
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AI Rules (Parallel)                                                 │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│ │ AI Rule #1  │  │ AI Rule #2  │  │ AI Rule #N  │                   │
│ │  (1-3s)     │  │  (1-3s)     │  │   (1-3s)    │                   │
│ └─────────────┘  └─────────────┘  └─────────────┘                   │
│        │               │               │                            │
│        └───────────────┼───────────────┘                            │
│                        ▼                                            │
│              First Match Wins                                       │
│              (Early Termination)                                    │
└─────────────────────────────────────────────────────────────────────┘
    │ (No matches)
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Fallback Strategy                                                   │
│ • No rules defined: Default AI moderation                           │
│ • Rules exist but no matches: Approve by default                    │
│ • Low confidence results: Flag for manual review                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Performance Optimizations

### 1. Caching Strategy

#### Rule Caching
- **TTL**: 5 minutes
- **Storage**: In-memory dictionary
- **Benefits**: Reduces database queries by ~90%
- **Invalidation**: Automatic expiry + manual invalidation

#### AI Result Caching
- **TTL**: 1 hour
- **Storage**: In-memory with size limits
- **Key**: MD5 hash of content + prompt
- **Benefits**: Avoids duplicate OpenAI API calls

### 2. Parallel Processing

#### AI Rules
- **ThreadPoolExecutor**: Up to 10 concurrent workers
- **Early Termination**: Stop on first match
- **Timeout**: 30 seconds per rule
- **Benefit**: ~3x faster than sequential processing

#### Connection Pooling
- **HTTP/2**: Enabled for OpenAI connections
- **Keep-alive**: 60-second expiry
- **Pool Size**: 50 keep-alive + 200 total connections

### 3. Database Optimizations

#### Bulk Operations
- **Bulk Insert**: Moderation results saved in batches
- **Connection Pooling**: SQLAlchemy connection reuse
- **Indexes**: Optimized for common queries

#### Query Optimization
- **Eager Loading**: Relationships loaded efficiently
- **Pagination**: All list endpoints paginated
- **Selective Fields**: Only required data fetched

## Scalability Considerations

### 1. Horizontal Scaling

#### Application Servers
- **Stateless Design**: No server-specific state
- **Load Balancer**: Can distribute across multiple instances
- **Session Storage**: Database-backed sessions

#### Database Scaling
- **Read Replicas**: Statistics queries can use replicas
- **Connection Pooling**: Efficient connection management
- **Partitioning**: Large tables can be partitioned by project

### 2. Resource Management

#### Memory Usage
- **Cache Limits**: Automatic cleanup when limits exceeded
- **Object Pools**: Reuse of expensive objects
- **Garbage Collection**: Proper cleanup of temporary objects

#### CPU Usage
- **Async Operations**: WebSocket updates in background threads
- **Thread Limits**: Controlled concurrency for AI processing
- **Process Monitoring**: Resource usage tracking

### 3. External Dependencies

#### OpenAI API
- **Rate Limiting**: Respect API limits
- **Retry Logic**: Exponential backoff on failures
- **Circuit Breaker**: Fail fast when service unavailable
- **Cost Monitoring**: Track API usage and costs

## Security Architecture

### 1. Authentication & Authorization

#### Multi-layer Security
- **Session-based**: Web dashboard authentication
- **API Key**: Programmatic access authentication
- **Project Isolation**: Users only access their projects
- **Role-based**: Admin vs regular user permissions

### 2. Data Protection

#### Input Validation
- **Content Sanitization**: XSS prevention
- **SQL Injection**: SQLAlchemy ORM protection
- **Rate Limiting**: API abuse prevention
- **Size Limits**: Content length restrictions

#### Data Privacy
- **No Content Storage**: Content can be anonymized
- **User Tracking**: Optional user ID tracking
- **Data Retention**: Configurable retention policies
- **GDPR Compliance**: User data deletion capabilities

### 3. Infrastructure Security

#### Network Security
- **HTTPS**: TLS encryption for all traffic
- **CORS**: Configured for WebSocket connections
- **Firewall**: Database access restrictions
- **VPN**: Optional VPN access for admin functions

## Monitoring & Observability

### 1. Logging

#### Structured Logging
- **DEBUG**: Technical details (cache hits, rule evaluation)
- **INFO**: Business events (content decisions, timing)
- **ERROR**: Problems requiring attention
- **Performance**: Processing times and bottlenecks

### 2. Metrics

#### Application Metrics
- **Throughput**: Requests per second
- **Latency**: Response time percentiles
- **Error Rate**: Failed requests percentage
- **Resource Usage**: Memory, CPU, connections

#### Business Metrics
- **Moderation Stats**: Approval/rejection rates
- **Rule Performance**: Accuracy and timing
- **User Behavior**: Violation patterns
- **Cost Tracking**: OpenAI API usage

### 3. Health Checks

#### System Health
- **Database**: Connection and query performance
- **OpenAI**: API connectivity and response times
- **Cache**: Hit rates and memory usage
- **WebSocket**: Connection counts and event rates

## Next Steps

- [Installation Guide](installation.md) - Set up AutoModerate
- [API Documentation](../api/overview.md) - Integrate with your app