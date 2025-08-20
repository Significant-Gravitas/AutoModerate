# AutoModerate Docker Setup

This directory contains all the necessary files to run AutoModerate as a Docker container setup.

## Quick Start

1. **Configure environment variables:**
   ```bash
   cp .env.docker.example .env
   # Edit .env and add your OPENAI_API_KEY and other configurations
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Web interface: http://localhost:6217
   - Default login: admin@automoderate.com / secure-admin-password-change-this

## Files Overview

- **Dockerfile**: Multi-stage Python application container
- **docker-compose.yml**: Complete stack with PostgreSQL
- **.dockerignore**: Excludes unnecessary files from build context
- **.env.docker**: Environment template (copy to .env)
- **README.md**: This documentation

## Services

### AutoModerate Application
- **Port**: 6217
- **Dependencies**: PostgreSQL
- **Volumes**: Persistent data storage

### PostgreSQL Database
- **Port**: 5432 (exposed for debugging)
- **Database**: automoderate
- **User**: automod_user


## Environment Configuration

Required variables in `.env`:

```bash
# Essential Configuration
OPENAI_API_KEY=your-api-key-here
SECRET_KEY=your-secure-secret-key
ADMIN_EMAIL=admin@automoderate.com
ADMIN_PASSWORD=your-secure-password

# Database (automatically configured for container)
DATABASE_URL=postgresql://automod_user:automod_password@postgres:5432/automoderate
```

## Troubleshooting

### Common Issues

1. **Database connection errors:**
   ```bash
   docker-compose logs postgres
   docker-compose restart automoderate
   ```

2. **Permission issues:**
   ```bash
   docker-compose down
   docker volume rm docker_postgres_data
   docker-compose up -d
   ```

3. **Port conflicts:**
   ```bash
   # Check port usage
   netstat -tulpn | grep :6217
   
   # Use different ports in docker-compose.yml
   ports:
     - "8080:6217"  # External:Internal
   ```

### Logs and Debugging

```bash
# View application logs
docker-compose logs -f automoderate

# View all service logs
docker-compose logs -f

# Access application shell
docker-compose exec automoderate bash

# Access database shell
docker-compose exec postgres psql -U automod_user automoderate
```

## Data Persistence

Data is persisted in Docker volumes:

- `postgres_data`: Database files
- `app_data`: Application files (uploads, logs)

To backup volumes:
```bash
docker run --rm -v docker_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```
