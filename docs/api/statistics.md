# Statistics API

The Statistics API provides detailed analytics and insights about your content moderation activities.

## Get Project Statistics

Retrieve comprehensive statistics for your project's moderation activity.

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
    "total_content": 15420,
    "approved": 12936,
    "rejected": 2180,
    "flagged": 304,
    "pending": 0,
    "approval_rate": 83.9,
    "rejection_rate": 14.1,
    "flag_rate": 2.0,
    "time_period": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-15T23:59:59Z",
      "days": 15
    },
    "processing_stats": {
      "avg_processing_time": 1.23,
      "total_processing_time": 18967.8,
      "fastest_processing": 0.05,
      "slowest_processing": 4.12
    },
    "rule_stats": {
      "keyword_matches": 1205,
      "regex_matches": 89,
      "ai_matches": 1190,
      "manual_reviews": 304
    },
    "user_stats": {
      "unique_users": 2847,
      "top_violators": [
        {
          "user_id": "user_12345",
          "violations": 23,
          "approval_rate": 45.2
        }
      ]
    }
  }
}
```

### Statistics Breakdown

#### Overall Metrics
- **total_content**: Total number of content items moderated
- **approved**: Number of approved content items
- **rejected**: Number of rejected content items  
- **flagged**: Number of items flagged for manual review
- **pending**: Number of items still being processed
- **approval_rate**: Percentage of content approved
- **rejection_rate**: Percentage of content rejected
- **flag_rate**: Percentage of content flagged

#### Performance Metrics
- **avg_processing_time**: Average time to moderate content (seconds)
- **total_processing_time**: Total processing time across all content
- **fastest_processing**: Fastest moderation time recorded
- **slowest_processing**: Slowest moderation time recorded

#### Rule Performance
- **keyword_matches**: Content caught by keyword rules
- **regex_matches**: Content caught by regex rules
- **ai_matches**: Content caught by AI rules
- **manual_reviews**: Content requiring human review

### Example Request

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/stats
```

## Get Detailed Analytics

Get more detailed analytics with time-based breakdowns and filtering options.

### Endpoint

```http
GET /api/analytics
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period: `hour`, `day`, `week`, `month` |
| `start_date` | string | Start date (ISO 8601 format) |
| `end_date` | string | End date (ISO 8601 format) |
| `group_by` | string | Group results by: `rule`, `user`, `content_type` |
| `rule_id` | string | Filter by specific rule ID |
| `user_id` | string | Filter by specific user ID |

### Response

```json
{
  "success": true,
  "analytics": {
    "summary": {
      "total_content": 5240,
      "time_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-07T23:59:59Z"
      }
    },
    "timeline": [
      {
        "date": "2024-01-01",
        "approved": 120,
        "rejected": 15,
        "flagged": 3,
        "total": 138
      },
      {
        "date": "2024-01-02", 
        "approved": 98,
        "rejected": 22,
        "flagged": 5,
        "total": 125
      }
    ],
    "rule_breakdown": [
      {
        "rule_id": "rule_123",
        "rule_name": "Spam Detection",
        "matches": 145,
        "accuracy": 92.3,
        "false_positives": 8
      }
    ],
    "content_types": {
      "text": 4820,
      "html": 285,
      "markdown": 135
    },
    "geographic_data": [
      {
        "country": "US",
        "total": 2100,
        "approved": 1890,
        "rejected": 210
      }
    ]
  }
}
```

### Example Requests

#### Weekly Analytics

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/analytics?period=day&start_date=2024-01-01&end_date=2024-01-07"
```

#### Rule Performance Analysis

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/analytics?group_by=rule&period=week"
```

#### User Behavior Analysis

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/analytics?group_by=user&user_id=user_12345"
```

## Rule Performance Metrics

Get detailed performance metrics for your moderation rules.

### Endpoint

```http
GET /api/rules/performance
```

### Response

```json
{
  "success": true,
  "rule_performance": [
    {
      "rule_id": "rule_123",
      "rule_name": "Spam Detection",
      "rule_type": "ai_prompt",
      "total_matches": 456,
      "accuracy_score": 94.2,
      "false_positive_rate": 5.8,
      "false_negative_rate": 2.1,
      "avg_processing_time": 1.45,
      "confidence_distribution": {
        "high": 298,
        "medium": 134,
        "low": 24
      },
      "last_updated": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Rule Metrics Explained

- **total_matches**: Number of times the rule was triggered
- **accuracy_score**: Overall accuracy percentage
- **false_positive_rate**: Percentage of incorrect rejections
- **false_negative_rate**: Percentage of missed violations
- **avg_processing_time**: Average time to evaluate the rule
- **confidence_distribution**: Breakdown of confidence levels

## User Statistics

Get statistics about user behavior and patterns.

### Endpoint

```http
GET /api/users/stats
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Number of users to return (default: 100) |
| `sort_by` | string | Sort by: `violations`, `approval_rate`, `total_content` |
| `min_content` | integer | Minimum content submissions required |

### Response

```json
{
  "success": true,
  "user_stats": [
    {
      "user_id": "user_12345",
      "total_submissions": 89,
      "approved": 67,
      "rejected": 18,
      "flagged": 4,
      "approval_rate": 75.3,
      "avg_processing_time": 1.2,
      "first_submission": "2024-01-01T10:00:00Z",
      "last_submission": "2024-01-15T16:30:00Z",
      "risk_score": 3.2,
      "violations_by_rule": {
        "spam_detection": 12,
        "inappropriate_content": 6
      }
    }
  ],
  "summary": {
    "total_users": 2847,
    "active_users": 1234,
    "high_risk_users": 45
  }
}
```

### Example Request

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/users/stats?sort_by=violations&limit=50"
```

## Export Data

Export your moderation data in various formats for external analysis.

### Endpoint

```http
GET /api/export
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | Export format: `csv`, `json`, `xlsx` |
| `type` | string | Data type: `content`, `rules`, `users`, `analytics` |
| `start_date` | string | Start date for data export |
| `end_date` | string | End date for data export |
| `include_content` | boolean | Include actual content text (default: false) |

### Response

The response will be a downloadable file in the requested format.

### Example Requests

#### Export Content Data as CSV

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/export?format=csv&type=content&start_date=2024-01-01" \
  -o moderation_data.csv
```

#### Export Analytics as JSON

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/export?format=json&type=analytics" \
  -o analytics_data.json
```

## Real-time Statistics Dashboard

For real-time statistics updates, use the WebSocket connection:

### WebSocket Event: `stats_update`

```javascript
const socket = io('http://localhost:6217');

// Join project room
socket.emit('join_project', {project_id: 'your-project-id'});

// Listen for real-time stats updates
socket.on('stats_update', function(data) {
    console.log('Updated stats:', data);
    // Update your dashboard UI
    updateDashboard(data);
});
```

### Stats Update Data

```json
{
  "total_content": 15421,
  "approved": 12937,
  "rejected": 2180,
  "flagged": 304,
  "approval_rate": 83.9,
  "recent_activity": [
    {
      "content_id": "content_123",
      "decision": "approved",
      "timestamp": "2024-01-15T16:45:30Z"
    }
  ]
}
```

## Custom Metrics

Define and track custom metrics specific to your use case.

### Create Custom Metric

```http
POST /api/metrics/custom
```

### Request Body

```json
{
  "name": "user_satisfaction",
  "description": "Track user satisfaction with moderation decisions",
  "type": "counter",
  "labels": ["decision", "content_type"]
}
```

### Track Custom Metric

```http
POST /api/metrics/custom/user_satisfaction/increment
```

```json
{
  "value": 1,
  "labels": {
    "decision": "approved",
    "content_type": "text"
  }
}
```

## Error Responses

### Invalid Date Range

```json
{
  "success": false,
  "error": "Invalid date range. End date must be after start date."
}
```

### Insufficient Data

```json
{
  "success": false,
  "error": "Insufficient data for the requested time period."
}
```

### Export Limit Exceeded

```json
{
  "success": false,
  "error": "Export limit exceeded. Maximum 100,000 records per export."
}
```

## Next Steps

- [WebSocket Events](websockets.md) - Real-time statistics updates
- [Project Management](projects.md) - Configure rules and settings
- [Moderation API](moderation.md) - Submit content for analysis