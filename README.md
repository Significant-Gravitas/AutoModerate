# AutoModerate - Content Moderation Platform

A comprehensive Flask-based content moderation platform that uses OpenAI for intelligent content analysis with real-time WebSocket updates.

## Features

- **User Authentication & Project Management**: Secure login system with project-based organization
- **API Key Management**: Generate and manage API keys for each project
- **Multiple Content Types**: Support for text, images, and other content types
- **Custom Moderation Rules**: Create keyword, regex, and AI-prompt based rules
- **OpenAI Integration**: Leverage OpenAI's moderation API and GPT models
- **Real-time Updates**: WebSocket-powered live updates for moderation results
- **RESTful API**: Complete API for content submission and retrieval
- **Admin Dashboard**: Web-based interface for managing projects and viewing analytics

## Architecture

The platform is built with a modular architecture:

```
AutoModerate/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API and web routes
│   ├── services/        # Business logic (OpenAI, Moderation)
│   ├── templates/       # HTML templates
│   ├── static/          # CSS, JS assets
│   └── utils/           # Utility functions
├── config/              # Configuration files
├── migrations/          # Database migrations
├── tests/               # Test files
└── run.py              # Application entry point
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Bentlybro/AutoModerate
cd AutoModerate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your OpenAI API key
# OPENAI_API_KEY=your-actual-openai-api-key-here
```

### 3. Run the Application

```bash
# Start the development server
python run.py
```

The application will be available at `http://localhost:6217` (configured in run.py)

### 4. Default Login

- **Email**: admin@example.com
- **Password**: admin123

## API Usage

### Authentication

All API requests require an API key in the header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:6217/api/moderate
```

### Submit Content for Moderation

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "type": "text",
    "content": "This is some content to moderate",
    "metadata": {"source": "user_comment"}
  }' \
  http://localhost:6217/api/moderate
```

### Response Format

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
      "moderator_type": "ai"
    }
  ]
}
```

### Get Content Status

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/content/content-id-here
```

### List Content

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:6217/api/content?page=1&per_page=20&status=approved"
```

### Get Statistics

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:6217/api/stats
```

## Moderation Rules

### Rule Types

1. **Keyword Rules**: Block content containing specific words
2. **Regex Rules**: Use regular expressions for pattern matching
3. **AI Prompt Rules**: Custom AI analysis with specific prompts

### Creating Rules via Dashboard

1. Navigate to your project
2. Go to "Moderation Rules"
3. Click "Create Rule"
4. Configure rule parameters
5. Set priority and action (approve/reject/flag)

## Database Models

### Core Models

- **User**: Platform users with authentication
- **Project**: Containers for moderation configurations
- **APIKey**: Authentication tokens for API access
- **Content**: Submitted content awaiting/completed moderation
- **ModerationRule**: Custom rules for content filtering
- **ModerationResult**: Results from moderation processes

## Configuration

### Environment Variables

```bash
# Flask Configuration
FLASK_ENV=development|production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///automoderate.db

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Application Settings
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

### Database Configuration

The platform uses SQLAlchemy with SQLite by default. For production, configure a PostgreSQL or MySQL database:

```bash
DATABASE_URL=postgresql://user:password@localhost/automoderate
```

## Deployment

### Production Considerations

1. **Environment Variables**: Set secure values for all environment variables
2. **Database**: Use a production database (PostgreSQL recommended)
3. **Web Server**: Use Gunicorn with Nginx
4. **SSL**: Enable HTTPS for secure API communication
5. **Monitoring**: Implement logging and monitoring

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "run.py"]
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/moderate` | Submit content for moderation |
| GET | `/api/content/<id>` | Get specific content |
| GET | `/api/content` | List content with pagination |
| GET | `/api/stats` | Get moderation statistics |
| GET | `/api/health` | Health check |

### Authentication

- **Web Interface**: Session-based authentication
- **API**: API key authentication via `X-API-Key` header

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API examples

## Roadmap

- [ ] Support for photo moderation
- [ ] Webhook notifications
- [ ] Multi-language support