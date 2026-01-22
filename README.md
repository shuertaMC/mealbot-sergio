# Mealbot - Meal Pairing Service

A Python/FastAPI-based RESTful service for managing lunch/meal pairings within organizations.

## Overview

Mealbot helps organizations create randomized meal pairings among members, ensuring diverse interactions while avoiding recent repeat pairings. The service manages organizations, members, rounds, and pairs through a REST API with Auth0 JWT authentication.

## Features

- **Organization Management**: Create and manage organizations with configurable pairing settings
- **Member Management**: CRUD operations for members with CSV import support
- **Pairing Algorithm**: Smart pairing that avoids recent repeats and handles odd/even member counts
- **Email Notifications**: Automated pairing notifications via Mailgun
- **Auth0 Integration**: Secure JWT-based authentication
- **PostgreSQL Backend**: Async database operations with SQLAlchemy

## Tech Stack

- **Python**: 3.11.x (or 3.10+)
- **Web Framework**: FastAPI 0.115.x with Uvicorn ASGI server
- **Database**: PostgreSQL with asyncpg driver
- **ORM**: SQLAlchemy 2.0.x (async)
- **Migrations**: Alembic
- **Authentication**: Auth0 JWT validation via python-jose
- **Email**: Mailgun HTTP API via httpx
- **Testing**: pytest with pytest-asyncio

## Prerequisites

- Python 3.10 or higher
- PostgreSQL database
- Auth0 account for JWT authentication
- Mailgun account for email notifications

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mealbot-sergio-test
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration values
   ```

5. **Set up the database**:
   ```bash
   # Create the database
   createdb mealbot

   # Run migrations
   alembic upgrade head
   ```

## Configuration

All configuration is managed through environment variables. See `.env.example` for a complete list of required and optional settings.

### Required Environment Variables

- `DATABASE_USER`: PostgreSQL user
- `DATABASE_NAME`: PostgreSQL database name
- `MAILGUN_API_KEY`: Mailgun API key
- `MAILGUN_DOMAIN`: Mailgun domain
- `MAILGUN_SMTP_LOGIN`: Mailgun SMTP login

### Optional Environment Variables (with defaults)

- `DATABASE_PASSWORD`: PostgreSQL password (default: empty)
- `DATABASE_HOST`: PostgreSQL host (default: localhost)
- `DATABASE_PORT`: PostgreSQL port (default: 5432)
- `AUTH0_DOMAIN`: Auth0 domain (default: mealbot.auth0.com)
- `AUTH0_AUDIENCE`: Auth0 audience (default: https://mealbot-2.herokuapp.com/)
- `PORT`: Application port (default: 8080)
- `ENVIRONMENT`: Environment name (default: dev)

## Running the Application

Start the development server:

```bash
uvicorn app.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`.

## API Documentation

Once the server is running, interactive API documentation is available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
mealbot-sergio-test/
├── app/                    # Application code
│   ├── __init__.py
│   ├── main.py            # FastAPI app initialization
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection setup
│   ├── dependencies.py    # Shared dependencies
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response models
│   ├── routers/           # API route handlers
│   ├── services/          # Business logic
│   └── middleware/        # Custom middleware
├── static/                # Static files (privacy.html, sample.csv)
├── tests/                 # Test suite
├── alembic/               # Database migrations
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # This file
```

## Development Guidelines

- Use async/await for all database and I/O operations
- Follow type hints throughout the codebase
- Maintain test coverage above 80%
- Run tests before committing changes
- Follow PEP 8 style guidelines

---

**Source**: https://github.com/shuertaMC/mealbot-sergio-test.git
**Created**: Thu Jan 22 19:59:22 UTC 2026
