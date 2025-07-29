# AutoModerate Documentation

Welcome to the AutoModerate documentation! This comprehensive guide covers everything you need to know about the AutoModerate content moderation platform.

## 📚 Documentation Overview

### Getting Started
- [**Installation & Setup**](guides/installation.md) - Get AutoModerate running locally or in production
- [**Quick Start Guide**](guides/quickstart.md) - Your first moderation project in 5 minutes
- [**Configuration**](guides/configuration.md) - Environment variables and settings

### API Documentation
- [**API Overview**](api/overview.md) - Authentication, rate limits, and general API info
- [**Content Moderation**](api/moderation.md) - Submit and retrieve moderated content
- [**Project Management**](api/projects.md) - Manage projects and API keys
- [**Statistics**](api/statistics.md) - Get moderation statistics and analytics
- [**WebSocket Events**](api/websockets.md) - Real-time updates and notifications

### Architecture & Development
- [**System Architecture**](guides/architecture.md) - How AutoModerate is built
- [**Moderation Rules**](guides/moderation-rules.md) - Keyword, regex, and AI-based rules
- [**Service Architecture**](guides/services.md) - Modular service design and components
- [**Database Schema**](guides/database.md) - Models and relationships

### Deployment & Operations
- [**Deployment Guide**](guides/deployment.md) - Production deployment options
- [**Monitoring & Logging**](guides/monitoring.md) - Observability and troubleshooting
- [**Performance Tuning**](guides/performance.md) - Optimization tips and best practices

## 🚀 What is AutoModerate?

AutoModerate is a comprehensive Flask-based content moderation platform that uses OpenAI for intelligent content analysis with real-time WebSocket updates. It provides:

- **Multi-layered Moderation**: Keyword, regex, and AI-powered content filtering
- **Real-time Updates**: WebSocket-powered live notifications
- **Project-based Organization**: Manage multiple moderation contexts
- **RESTful API**: Complete API for integration with any application
- **Web Dashboard**: User-friendly interface for managing rules and viewing analytics
- **Scalable Architecture**: Modular design with parallel processing

## 🔧 Core Features

### Content Moderation
- **Text Analysis**: Advanced text moderation with customizable rules
- **Image Support**: Ready for image content moderation
- **Multiple Rule Types**: Keyword blocking, regex patterns, and AI prompts
- **Parallel Processing**: Fast AI rule evaluation with early termination

### Real-time Operations
- **WebSocket Integration**: Live updates for moderation results
- **Project Rooms**: Isolated real-time channels per project
- **Instant Notifications**: Immediate feedback on content decisions

### Management & Analytics
- **User Authentication**: Secure login and project access control
- **API Key Management**: Generate and manage project-specific API keys
- **Comprehensive Statistics**: Detailed analytics and reporting
- **Manual Review Queue**: Human oversight for edge cases

## 🏗 Architecture Highlights

AutoModerate features a clean, modular architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   API Client     │    │  WebSocket      │
│   Dashboard     │    │   Integration    │    │  Real-time      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │     Flask Application   │
                    │  ┌─────────────────────┐│
                    │  │ ModerationOrchestrator││
                    │  └─────────────────────┘│
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Modular Services      │
                    │  ┌──────────┬─────────┐ │
                    │  │Moderation│   AI    │ │
                    │  │ Services │Services │ │
                    │  └──────────┴─────────┘ │
                    └─────────────────────────┘
```

## 🔗 Quick Links

- **GitHub Repository**: [AutoModerate](https://github.com/your-username/automoderate)
- **API Base URL**: `http://localhost:6217/api` (development)
- **Web Dashboard**: `http://localhost:6217/dashboard`
- **Default Login**: `admin@example.com` / `admin123`

## 📖 Getting Help

- Check the [Installation Guide](guides/installation.md) for setup issues
- Review [API Documentation](api/overview.md) for integration questions
- See [Architecture Guide](guides/architecture.md) for development questions
- Look at [Performance Guide](guides/performance.md) for optimization tips

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines and feel free to submit issues and pull requests.

---

**Need help?** Start with the [Quick Start Guide](guides/quickstart.md) or check out the [API Overview](api/overview.md)!