# API Overview

The AutoModerate API provides programmatic access to content moderation services. All API endpoints are RESTful and return JSON responses.

## Base URL

```
http://localhost:6217/api
```

For production deployments, replace `localhost:6217` with your domain.

## Available Endpoints

AutoModerate provides the following API endpoints:

- **POST /moderate** - Submit content for moderation
- **GET /content/{id}** - Get specific content details
- **GET /content** - List moderated content with pagination
- **GET /stats** - Get basic project statistics
- **GET /health** - API health check (no authentication required)
- **GET /docs** - API documentation page (no authentication required)

## Authentication

All API endpoints (except `/health` and `/docs`) require authentication using an API key.

### API Key Header

Include your API key in the request header:

```http
X-API-Key: your-api-key-here
```

### Getting an API Key

API keys are generated and managed through the AutoModerate web dashboard. Each API key is project-specific and provides access only to that project's data.

## Request Format

- **Content-Type**: `application/json` (for POST requests)
- **Method**: Specified per endpoint (GET, POST)
- **Headers**: Must include `X-API-Key` for authenticated endpoints

### Example Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "text",
    "content": "This is content to moderate",
    "metadata": {"user_id": "user123", "source": "comment_system"}
  }' \
  http://localhost:6217/api/moderate
```

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "content_id": "uuid-here",
  "status": "approved",
  "moderation_results": [...]
}
```

### Error Response

```json
{
  "error": "Error message describing what went wrong"
}
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing API key |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

## Content Types

AutoModerate currently supports:

- **text**: Plain text content (default)

## Metadata

Optional metadata can be included with content submissions:

```json
{
  "metadata": {
    "user_id": "user123",
    "source": "comment_system",
    "custom_field": "custom_value"
  }
}
```

**Note**: If `user_id` is provided, AutoModerate will track the user and link them to the content submission.

## Pagination

The `/content` endpoint supports pagination using query parameters:

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `status`: Filter by status (`approved`, `rejected`, `flagged`, `pending`)

### Pagination Response

```json
{
  "success": true,
  "content": [...],
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

## Error Handling

### Common Errors

```json
// Missing API key
{
  "error": "API key required"
}

// Invalid API key
{
  "error": "Invalid API key"
}

// Missing required field
{
  "error": "JSON data required"
}

// Missing content
{
  "error": "Content data required"
}

// Content not found
{
  "error": "Content not found"
}
```

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
- [WebSocket Events](websockets.md) - Real-time updates
- [Installation Guide](../guides/installation.md) - Set up AutoModerate
- [Architecture Guide](../guides/architecture.md) - Understand the system