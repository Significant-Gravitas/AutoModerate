# Content Moderation API

The Content Moderation API allows you to submit content for automated moderation and retrieve moderation results.

## Submit Content for Moderation

Submit content to be analyzed by your project's moderation rules.

### Endpoint

```http
POST /api/moderate
```

### Headers

```http
Content-Type: application/json
X-API-Key: your-api-key
```

### Request Body

```json
{
  "type": "text",
  "content": "The content to be moderated",
  "metadata": {
    "user_id": "optional-user-id",
    "source": "comment_system",
    "custom_field": "custom_value"
  }
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | Content type (defaults to "text") |
| `content` | string | Yes | The actual content to moderate |
| `metadata` | object | No | Additional information about the content |

#### Metadata Fields

The `metadata` object can contain any custom fields. If `user_id` is provided, AutoModerate will track per-user statistics.

### Response

```json
{
  "success": true,
  "content_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "approved",
  "moderation_results": [
    {
      "decision": "approved",
      "confidence": 0.95,
      "reason": "Content passed all moderation checks",
      "moderator_type": "rule",
      "rule_name": "Safe Content Rule",
      "processing_time": 0.15
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the request was successful |
| `content_id` | string | Unique identifier for the moderated content |
| `status` | string | Moderation decision: `approved`, `rejected`, `flagged` |
| `moderation_results` | array | Detailed results from moderation process |

### Example Requests

#### Simple Text Moderation

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "text",
    "content": "This is a great product! I love it."
  }' \
  http://localhost:6217/api/moderate
```

#### Content with User Tracking

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "Check out this amazing deal!",
    "metadata": {
      "user_id": "user_12345",
      "source": "product_review"
    }
  }' \
  http://localhost:6217/api/moderate
```

## Get Content Details

Retrieve detailed information about previously moderated content.

### Endpoint

```http
GET /api/content/{id}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | The unique identifier of the content |

### Response

```json
{
  "success": true,
  "content": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "project_id": "proj_abc123",
    "content_type": "text",
    "content_data": "The original content",
    "meta_data": {
      "user_id": "user_12345",
      "source": "comments"
    },
    "status": "approved",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:01",
    "moderation_results": [
      {
        "decision": "approved",
        "confidence": 0.95,
        "reason": "Content passed all checks",
        "moderator_type": "rule",
        "created_at": "2024-01-15T10:30:01"
      }
    ]
  }
}
```

### Example

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/content/123e4567-e89b-12d3-a456-426614174000
```

## List Content

Retrieve a paginated list of moderated content.

### Endpoint

```http
GET /api/content
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page (max: 100) |
| `status` | string | - | Filter by status: `approved`, `rejected`, `flagged` |

### Response

```json
{
  "success": true,
  "content": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "project_id": "proj_abc123",
      "content_type": "text",
      "content_data": "The content text",
      "meta_data": {
        "user_id": "user_12345"
      },
      "status": "approved",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:01",
      "moderation_results": []
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 5,
    "per_page": 20,
    "total": 100,
    "has_next": true,
    "has_prev": false
  }
}
```

### Example Requests

#### Get All Content

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/content
```

#### Get Rejected Content

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/content?status=rejected&page=1&per_page=50"
```

## Get Project Statistics

Retrieve basic statistics for your project's moderation activity. See [Project Statistics API](statistics.md) for detailed documentation.

### Endpoint

```http
GET /api/stats
```

### Headers

```http
X-API-Key: your-api-key
```

### Example Request

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/stats
```

## Health Check

Check the API service status.

### Endpoint

```http
GET /api/health
```

**Note**: This endpoint does not require authentication.

### Response

```json
{
  "status": "healthy",
  "service": "AutoModerate API",
  "version": "1.0.0"
}
```

### Example

```bash
curl http://localhost:6217/api/health
```

## API Documentation

Access the web-based API documentation.

### Endpoint

```http
GET /api/docs
```

This endpoint returns an HTML page with interactive API documentation.

## Authentication

All API endpoints (except `/health` and `/docs`) require authentication using an API key.

### API Key Header

Include your API key in the request header:

```http
X-API-Key: your-api-key-here
```

### Getting an API Key

1. Log in to the AutoModerate dashboard
2. Navigate to your project
3. Go to "API Keys" section
4. Click "Generate New Key"
5. Copy and securely store your key

## Error Responses

### Authentication Errors

#### Missing API Key

```json
{
  "error": "API key required"
}
```
HTTP Status: 401

#### Invalid API Key

```json
{
  "error": "Invalid API key"
}
```
HTTP Status: 401

### Request Errors

#### Missing JSON Data

```json
{
  "error": "JSON data required"
}
```
HTTP Status: 400

#### Missing Content

```json
{
  "error": "Content data required"
}
```
HTTP Status: 400

#### Content Not Found

```json
{
  "error": "Content not found"
}
```
HTTP Status: 404

### Server Errors

#### Internal Server Error

```json
{
  "error": "Internal server error"
}
```
HTTP Status: 500

## Moderation Statuses

AutoModerate uses four primary statuses for content:

- **pending**: Content is being processed
- **approved**: Content passed all moderation rules
- **rejected**: Content violated one or more moderation rules
- **flagged**: Content requires manual review

## Content Types

Currently supported content types:
- **text**: Plain text content (default)

## Best Practices

### 1. Always Handle Errors
```python
import requests

response = requests.post('/api/moderate', 
    headers={'X-API-Key': 'your-key'},
    json={'content': 'test content'}
)

if response.status_code == 200:
    data = response.json()
    if data['success']:
        print(f"Content {data['content_id']}: {data['status']}")
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")
else:
    print(f"HTTP Error: {response.status_code}")
```

### 2. Use Metadata for Tracking
Include useful metadata to track content sources and users:

```json
{
  "content": "User comment text",
  "metadata": {
    "user_id": "user_12345",
    "source": "comment_system",
    "post_id": "post_67890",
    "ip_address": "192.168.1.1"
  }
}
```

### 3. Implement Pagination
When listing content, always use pagination:

```bash
# Start with page 1
curl -H "X-API-Key: your-key" \
  "http://localhost:6217/api/content?page=1&per_page=50"

# Check pagination.has_next and continue if needed
```

### 4. Monitor Your Statistics
Regularly check your project statistics to understand moderation patterns:

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:6217/api/stats
```

## Next Steps

- [WebSocket Events](websockets.md) - Real-time moderation updates  
- [Installation Guide](../guides/installation.md) - Set up AutoModerate
- [Architecture Guide](../guides/architecture.md) - Understand the system