# AutoModerate Documentation

Welcome to the AutoModerate documentation! This guide covers everything you need to know about the AutoModerate content moderation platform.

## Documentation Overview

### Getting Started
- [**Installation & Setup**](guides/installation.md) - Get AutoModerate running locally or in production
- [**System Architecture**](guides/architecture.md) - How AutoModerate is built

### API Documentation
- [**API Overview**](api/overview.md) - Authentication and general API information
- [**Content Moderation**](api/moderation.md) - Submit and retrieve moderated content
- [**Project Statistics**](api/statistics.md) - Get basic moderation statistics
- [**WebSocket Events**](api/websockets.md) - Real-time updates and notifications

## What is AutoModerate?

AutoModerate is a Flask-based content moderation platform that uses OpenAI for intelligent content analysis with real-time WebSocket updates. It provides:

- **Multi-layered Moderation**: Keyword, regex, and AI-powered content filtering
- **Real-time Updates**: WebSocket-powered live notifications
- **Project-based Organization**: Manage multiple moderation contexts
- **RESTful API**: Complete API for integration with any application
- **Scalable Architecture**: Modular design with parallel processing

## Core Features

### Content Moderation
- **Text Analysis**: Advanced text moderation with customizable rules
- **Multiple Rule Types**: Keyword blocking, regex patterns, and AI prompts
- **Parallel Processing**: Fast AI rule evaluation with early termination

### Real-time Operations
- **WebSocket Integration**: Live updates for moderation results
- **Project Rooms**: Isolated real-time channels per project
- **Instant Notifications**: Immediate feedback on content decisions

### Management & Analytics
- **API Key Management**: Generate and manage project-specific API keys
- **Basic Statistics**: Track approval, rejection, and flagging rates
- **Project Organization**: Multiple projects with isolated data

## Architecture Highlights

AutoModerate features a clean, modular architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   API Client     │    │  WebSocket      │
│   Dashboard     │    │   Integration    │    │  Real-time      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌───────────────────────────┐
                    │     Flask Application     │
                    │  ┌──────────────────────┐ │
                    │  │ModerationOrchestrator│ │
                    │  └──────────────────────┘ │
                    └───────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Modular Services      │
                    │  ┌──────────┬─────────┐ │
                    │  │Moderation│   AI    │ │
                    │  │ Services │Services │ │
                    │  └──────────┴─────────┘ │
                    └─────────────────────────┘
```

## Quick Links

- **API Base URL**: `http://localhost:6217/api` (development)
- **Health Check**: `http://localhost:6217/api/health`
- **Default Admin**: `admin@example.com` / `admin123`

## Getting Help

- Check the [Installation Guide](guides/installation.md) for setup issues
- Review [API Documentation](api/overview.md) for integration questions
- See [Architecture Guide](guides/architecture.md) for development questions

## Contributing

We welcome contributions! Please see our contributing guidelines and feel free to submit issues and pull requests.

## Available API Endpoints

- **POST /api/moderate** - Submit content for moderation
- **GET /api/content/{id}** - Get specific content details
- **GET /api/content** - List moderated content (with pagination)
- **GET /api/stats** - Get basic project statistics
- **GET /api/health** - API health check
- **GET /api/docs** - API documentation page

## WebSocket Events

- **connect** - Client connects to server
- **disconnect** - Client disconnects from server
- **join_project** - Join a project room for updates
- **leave_project** - Leave a project room

---

**Need help?** Start with the [Installation Guide](guides/installation.md) or check out the [API Overview](api/overview.md)