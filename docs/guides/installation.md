# Installation & Setup Guide

This guide will walk you through setting up AutoModerate on your local machine or server.

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **pip**: Python package installer
- **Git**: For cloning the repository
- **OpenAI API Key**: Required for AI moderation features

### Supported Platforms

- **Linux**: Ubuntu 18.04+, CentOS 7+, Debian 9+
- **macOS**: 10.14+
- **Windows**: Windows 10+

## Quick Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Significant-Gravitas/AutoModerate.git
cd AutoModerate
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your settings
nano .env  # or use your preferred editor
```

Required environment variables:
```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_CHAT_MODEL=gpt-5-nano-2025-08-07
OPENAI_CONTEXT_WINDOW=400000
OPENAI_MAX_OUTPUT_TOKENS=128000

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///instance/automoderate.db

# Admin User (Optional - uses defaults if not set)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

### 5. Run the Application

```bash
python run.py
```

The application will be available at `http://localhost:6217`

## Detailed Installation Options

### Option 1: Development Setup

Perfect for local development and testing.

```bash
# 1. Clone and enter directory
git clone https://github.com/your-username/AutoModerate.git
cd AutoModerate

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env

# 5. Configure your .env file
# Add your OPENAI_API_KEY and other settings

# 6. Run development server
python run.py
```

### Option 2: Production Setup

For production deployments with PostgreSQL and proper configuration.

```bash
# 1. System dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib nginx

# 2. Create database
sudo -u postgres createdb automoderate
sudo -u postgres createuser automoderate_user
sudo -u postgres psql -c "ALTER USER automoderate_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE automoderate TO automoderate_user;"

# 3. Application setup
git clone https://github.com/your-username/AutoModerate.git
cd AutoModerate
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Production environment
cp .env.example .env
# Edit .env with production settings:
# DATABASE_URL=postgresql://automoderate_user:secure_password@localhost/automoderate
# FLASK_ENV=production
# SECRET_KEY=very-secure-secret-key

# 5. Install and configure Gunicorn
pip install gunicorn
```

### Option 3: Docker Setup

Easy containerized deployment.

```bash
# 1. Clone repository
git clone https://github.com/your-username/AutoModerate.git
cd AutoModerate

# 2. Create .env file
cp .env.example .env
# Edit .env with your settings

# 3. Build and run with Docker Compose
docker-compose up -d
```

**Docker Compose Configuration** (`docker-compose.yml`):

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "6217:6217"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://automoderate:password@db:5432/automoderate
    env_file:
      - .env
    depends_on:
      - db
    volumes:
      - ./instance:/app/instance

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: automoderate
      POSTGRES_USER: automoderate
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory
RUN mkdir -p instance

# Expose port
EXPOSE 6217

# Run application
CMD ["python", "run.py"]
```

## Database Setup

### SQLite (Default)

SQLite is used by default and requires no additional setup. The database file will be created automatically at `instance/automoderate.db`.

### PostgreSQL (Recommended for Production)

```bash
# 1. Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# 2. Create database and user
sudo -u postgres psql

CREATE DATABASE automoderate;
CREATE USER automoderate_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE automoderate TO automoderate_user;
\q

# 3. Update .env file
DATABASE_URL=postgresql://automoderate_user:your_password@localhost/automoderate

# 4. Install PostgreSQL adapter
pip install psycopg2-binary
```

### MySQL/MariaDB

```bash
# 1. Install MySQL
sudo apt install mysql-server

# 2. Create database and user
sudo mysql

CREATE DATABASE automoderate;
CREATE USER 'automoderate_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON automoderate.* TO 'automoderate_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 3. Update .env file
DATABASE_URL=mysql://automoderate_user:your_password@localhost/automoderate

# 4. Install MySQL adapter
pip install PyMySQL
```

## OpenAI API Setup

### Getting an API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the key and add it to your `.env` file:

```env
OPENAI_API_KEY=sk-your-api-key-here
```

### API Key Security

**Important**: Never commit your API key to version control!

- Add `.env` to your `.gitignore` file
- Use environment variables in production
- Rotate keys regularly
- Monitor usage and costs

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for AI moderation |
| `OPENAI_CHAT_MODEL` | No | `gpt-5-nano-2025-08-07` | GPT model for analysis |
| `OPENAI_CONTEXT_WINDOW` | No | `400000` | Model context window size |
| `OPENAI_MAX_OUTPUT_TOKENS` | No | `128000` | Maximum output tokens |
| `FLASK_ENV` | No | `development` | Flask environment mode |
| `SECRET_KEY` | No | Generated | Flask secret key for sessions |
| `DATABASE_URL` | No | SQLite | Database connection string |
| `ADMIN_EMAIL` | No | `admin@example.com` | Default admin email |
| `ADMIN_PASSWORD` | No | `admin123` | Default admin password |
| `SQL_DEBUG` | No | `False` | Enable SQL query logging |

### Custom Configuration

Create a custom configuration file:

```python
# config/custom_config.py
import os
from config.config import Config

class CustomConfig(Config):
    # Custom settings
    MAX_CONTENT_LENGTH = 10000  # characters
    RATE_LIMIT_PER_HOUR = 2000
    CACHE_TTL = 600  # seconds
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
```

## Verification

### 1. Health Check

Test that the application is running:

```bash
curl http://localhost:6217/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "AutoModerate API",
  "version": "1.0.0"
}
```

### 2. Database Connection

Check database connectivity:

```bash
# From the application directory
python -c "
from app import create_app
from app import db
app = create_app()
with app.app_context():
    print('Database connection:', db.engine.url)
    print('Tables:', db.engine.table_names())
"
```

### 3. OpenAI Integration

Test OpenAI connectivity:

```bash
python -c "
from app.services.ai.openai_client import OpenAIClient
client = OpenAIClient()
success, message = client.test_connection()
print(f'OpenAI connection: {message}')
"
```

### 4. Web Interface

1. Open `http://localhost:6217` in your browser
2. You should see the login page
3. Log in with default credentials:
   - Email: `admin@example.com`
   - Password: `admin123`

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using port 6217
lsof -i :6217

# Kill the process if needed
kill -9 <PID>

# Or change the port in run.py
```

#### 2. OpenAI API Key Issues

```bash
# Test your API key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer your-api-key"
```

#### 3. Database Connection Errors

```bash
# For PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l | grep AutoModerate
```

#### 4. Permission Errors

```bash
# Fix file permissions
chmod +x run.py
chown -R $USER:$USER ./instance/
```

#### 5. Python Version Issues

```bash
# Check Python version
python --version
python3 --version

# Use specific Python version
python3.9 -m venv venv
```

### Log Files

Check application logs for errors:

```bash
# Development logs (console output)
python run.py

# Production logs
tail -f /var/log/automoderate/error.log
journalctl -u automoderate -f
```

### Getting Help

If you encounter issues:

1. Review log files for error messages
2. Verify all prerequisites are met
3. Check the application health endpoint: `http://localhost:6217/api/health`
4. Verify OpenAI API key is working correctly

## Next Steps

After successful installation:

1. [API Documentation](../api/overview.md) - Integrate with your application
2. [System Architecture](architecture.md) - Understand how AutoModerate works

## Security Checklist

Before deploying to production:

- [ ] Change default admin credentials
- [ ] Use a strong `SECRET_KEY`
- [ ] Configure HTTPS/SSL
- [ ] Set up proper database credentials
- [ ] Configure firewall rules
- [ ] Enable logging and monitoring
- [ ] Set up regular backups
- [ ] Review and configure rate limiting
- [ ] Secure your OpenAI API key