# Project Statistics API

Get basic statistics about your project's moderation activity.

## Get Project Statistics

Retrieve basic statistics for your project's content moderation activity.

### Endpoint

```http
GET /api/stats
```

### Headers

```http
X-API-Key: your-api-key
```

### Response

```json
{
  "success": true,
  "stats": {
    "total_content": 1542,
    "approved": 1293,
    "rejected": 218,
    "flagged": 31,
    "pending": 0,
    "approval_rate": 83.9
  }
}
```

### Statistics Fields

- **total_content**: Total number of content items moderated
- **approved**: Number of approved content items
- **rejected**: Number of rejected content items  
- **flagged**: Number of items flagged for manual review
- **pending**: Number of items still being processed
- **approval_rate**: Percentage of content approved (calculated as `approved / total_content * 100`)

### Example Request

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/stats
```

### Example Response

```json
{
  "success": true,
  "stats": {
    "total_content": 2847,
    "approved": 2456,
    "rejected": 315,
    "flagged": 76,
    "pending": 0,
    "approval_rate": 86.3
  }
}
```

## Status Definitions

- **approved**: Content passed all moderation rules and was approved
- **rejected**: Content violated one or more moderation rules and was rejected
- **flagged**: Content was flagged for manual review
- **pending**: Content is currently being processed (should typically be 0)

## Error Responses

### Missing API Key

```json
{
  "error": "API key required"
}
```
HTTP Status: 401

### Invalid API Key

```json
{
  "error": "Invalid API key"
}
```
HTTP Status: 401

### Internal Server Error

```json
{
  "error": "Internal server error"
}
```
HTTP Status: 500

## Usage Notes

- Statistics are calculated in real-time from your project's content database
- Only content belonging to your project (identified by API key) is included in the statistics
- The approval rate is calculated as `(approved_count / total_content_count) * 100`
- If there is no content in the project, `total_content` will be 0 and `approval_rate` will be 0

## Next Steps

- [Content Moderation API](moderation.md) - Submit content for moderation
- [Content Listing API](moderation.md#list-content) - List moderated content
- [WebSocket Events](websockets.md) - Real-time updates
- [API Overview](overview.md) - General API information