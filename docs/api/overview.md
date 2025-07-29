# API Overview

The AutoModerate API provides programmatic access to content moderation services. All API endpoints are RESTful and return JSON responses.

## Base URL

```
http://localhost:6217/api
```

For production deployments, replace `localhost:6217` with your domain.

## Authentication

All API requests require authentication using an API key. Include your API key in the request header:

```http
X-API-Key: your-api-key-here
```

### Getting an API Key

1. Log in to the AutoModerate dashboard
2. Navigate to your project
3. Go to "API Keys" section
4. Click "Generate New Key"
5. Copy and securely store your key

**Important**: API keys are project-specific and provide access only to that project's data.

## Request Format

- **Content-Type**: `application/json`
- **Method**: Specified per endpoint (GET, POST, etc.)
- **Headers**: Must include `X-API-Key`

### Example Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "text",
    "content": "This is content to moderate",
    "metadata": {"source": "user_comment"}
  }' \
  http://localhost:6217/api/moderate
```

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data here
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing API key |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Default Limit**: 1000 requests per hour per API key
- **Burst Limit**: 100 requests per minute
- **Headers Included**:
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

### Rate Limit Response

When rate limit is exceeded:

```json
{
  "success": false,
  "error": "Rate limit exceeded. Try again later.",
  "retry_after": 3600
}
```

## Pagination

List endpoints support pagination using query parameters:

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

### Pagination Response

```json
{
  "success": true,
  "data": [...],
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

## Content Types

AutoModerate supports various content types:

| Type | Description | Example |
|------|-------------|---------|
| `text` | Plain text content | Comments, messages, posts |
| `html` | HTML content (tags stripped for analysis) | Rich text content |
| `markdown` | Markdown formatted text | Documentation, articles |

## Metadata

Optional metadata can be included with content submissions:

```json
{
  "metadata": {
    "user_id": "user123",
    "source": "comment_system",
    "timestamp": "2024-01-15T10:30:00Z",
    "ip_address": "192.168.1.1",
    "custom_field": "custom_value"
  }
}
```

**Note**: If `user_id` is provided, AutoModerate will track per-user statistics.

## Error Handling

The API uses standard HTTP status codes and provides detailed error messages:

### Common Errors

```json
// Missing API key
{
  "success": false,
  "error": "API key required"
}

// Invalid API key
{
  "success": false,
  "error": "Invalid API key"
}

// Missing required field
{
  "success": false,
  "error": "Content data required"
}

// Invalid content type
{
  "success": false,
  "error": "Unsupported content type: video"
}
```

## SDKs and Libraries

Official SDKs are available for popular programming languages:

- **Python**: `pip install automoderate-python`
- **Node.js**: `npm install automoderate-js`
- **PHP**: `composer require automoderate/php-sdk`

### Python Example

```python
from automoderate import AutoModerateclient

client = AutoModerateClient(api_key="your-api-key")

result = client.moderate_content(
    content="This is some text to moderate",
    content_type="text",
    metadata={"user_id": "user123"}
)

print(f"Decision: {result.decision}")
print(f"Confidence: {result.confidence}")
```

## Webhooks

AutoModerate can send webhook notifications for moderation events:

- **Content Moderated**: When content moderation is complete
- **Manual Review Required**: When content is flagged for human review
- **Rule Triggered**: When specific moderation rules are matched

See [Webhooks Documentation](webhooks.md) for configuration details.

## Testing

Use the `/api/health` endpoint to test your API connection:

```bash
curl http://localhost:6217/api/health
```

Response:
```json
{
  "status": "healthy",
  "service": "AutoModerate API",
  "version": "1.0.0"
}
```

## Next Steps

- [Content Moderation API](moderation.md) - Submit content for moderation
- [Statistics API](statistics.md) - Get moderation analytics
- [WebSocket Events](websockets.md) - Real-time updates
- [Project Management](projects.md) - Manage projects and API keys