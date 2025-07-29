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
| `type` | string | Yes | Content type: `text`, `html`, `markdown` |
| `content` | string | Yes | The actual content to moderate |
| `metadata` | object | No | Additional information about the content |

#### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | Unique identifier for the content author |
| `source` | string | Source of the content (e.g., "comments", "posts") |
| `ip_address` | string | IP address of the content submitter |
| `timestamp` | string | ISO 8601 timestamp of content creation |

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

#### Moderation Result Object

| Field | Type | Description |
|-------|------|-------------|
| `decision` | string | `approved`, `rejected`, or `flagged` |
| `confidence` | number | Confidence score (0.0 to 1.0) |
| `reason` | string | Human-readable explanation |
| `moderator_type` | string | `rule`, `ai`, or `manual` |
| `rule_name` | string | Name of the triggered rule (if applicable) |
| `processing_time` | number | Time taken to process in seconds |

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
    "type": "text",
    "content": "Check out this amazing deal!",
    "metadata": {
      "user_id": "user_12345",
      "source": "product_review",
      "ip_address": "192.168.1.100"
    }
  }' \
  http://localhost:6217/api/moderate
```

#### HTML Content Moderation

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "html",
    "content": "<p>This is <strong>HTML content</strong> with <a href=\"#\">links</a>.</p>"
  }' \
  http://localhost:6217/api/moderate
```

## Get Content Details

Retrieve detailed information about previously moderated content.

### Endpoint

```http
GET /api/content/{content_id}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | Yes | The unique identifier of the content |

### Response

```json
{
  "success": true,
  "content": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "type": "text",
    "content": "The original content",
    "status": "approved",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:01Z",
    "metadata": {
      "user_id": "user_12345",
      "source": "comments"
    },
    "moderation_results": [
      {
        "decision": "approved",
        "confidence": 0.95,
        "reason": "Content passed all checks",
        "moderator_type": "rule",
        "created_at": "2024-01-15T10:30:01Z"
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
| `user_id` | string | - | Filter by user ID |
| `since` | string | - | ISO 8601 date, content created after this date |
| `until` | string | - | ISO 8601 date, content created before this date |

### Response

```json
{
  "success": true,
  "content": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "type": "text",
      "status": "approved",
      "created_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "user_id": "user_12345"
      }
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

#### Get Content by User

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/content?user_id=user_12345"
```

#### Get Recent Content

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/content?since=2024-01-15T00:00:00Z"
```

## Moderation Statuses

AutoModerate uses three primary statuses for content:

### Approved ✅
- Content passed all moderation rules
- Safe to display to users
- No further action required

### Rejected ❌
- Content violated one or more moderation rules
- Should not be displayed to users
- May require notification to content author

### Flagged 🚩
- Content requires manual review
- Uncertain moderation decision
- Should be reviewed by human moderators

## Error Responses

### Missing Content

```json
{
  "success": false,
  "error": "Content not found"
}
```

### Invalid Content Type

```json
{
  "success": false,
  "error": "Invalid content type. Supported types: text, html, markdown"
}
```

### Missing Required Fields

```json
{
  "success": false,
  "error": "Content data required"
}
```

### Rate Limit Exceeded

```json
{
  "success": false,
  "error": "Rate limit exceeded. Try again later.",
  "retry_after": 3600
}
```

## Best Practices

### 1. Handle Async Processing
Moderation can take 1-3 seconds for AI rules. Consider:
- Showing loading states to users
- Using WebSocket updates for real-time results
- Implementing proper timeout handling

### 2. Implement Retry Logic
```python
import time
import requests

def moderate_with_retry(content, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post('/api/moderate', json={
                'type': 'text',
                'content': content
            })
            return response.json()
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### 3. Use Metadata Effectively
Include useful metadata for tracking and analytics:
```json
{
  "metadata": {
    "user_id": "user_12345",
    "source": "comment_system",
    "post_id": "post_67890",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "referrer": "https://example.com/post/123"
  }
}
```

### 4. Monitor Performance
Track moderation performance:
- Average processing time
- Rule match rates
- False positive/negative rates
- User satisfaction scores

## Next Steps

- [Statistics API](statistics.md) - Get moderation analytics
- [WebSocket Events](websockets.md) - Real-time moderation updates  
- [Project Management](projects.md) - Manage rules and settings