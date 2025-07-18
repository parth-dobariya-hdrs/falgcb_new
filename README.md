# ================================

# FILE: README.md

# ================================

# FastAPI LangGraph Chatbot

A production-ready chatbot API built with FastAPI, LangGraph, and PostgreSQL checkpointer for persistent conversation
memory.

## Features

- **FastAPI** for high-performance API
- **LangGraph** for advanced conversation flow
- **PostgreSQL** for persistent conversation memory
- **Groq** LLM integration
- **Tavily** search tool integration
- **Docker** support for easy deployment
- **CORS** enabled for frontend integration

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd fastapi-langgraph-chatbot
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your API keys:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
PSQL_PASSWORD=your_secure_password
SECRET_KEY=your-secret-key-here
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Test the API

Visit http://localhost:8000/docs for interactive API documentation.

## API Endpoints

### Chat Endpoints

- `POST /api/v1/chat/message` - Send a message to the chatbot
- `GET /api/v1/chat/history/{thread_id}` - Get chat history
- `DELETE /api/v1/chat/history/{thread_id}` - Clear chat history

### System Endpoints

- `GET /api/v1/system/health` - Health check

## Usage Example

```python
import httpx

# Send a message
response = httpx.post(
    "http://localhost:8000/api/v1/chat/message",
    json={
        "message": "Hello, what's the weather like today?",
        "thread_id": "user-123"
    }
)

print(response.json())
```

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run PostgreSQL (or use Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=your_password postgres:15

# Run the application
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest tests/
```

## Architecture

The application follows FastAPI best practices with:

- **Layered Architecture**: API → Services → Core
- **Dependency Injection**: Database and AI components
- **Async/Await**: Throughout for performance
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging for debugging

## Configuration

Key configuration options in `app/core/config.py`:

- Database connection settings
- CORS origins
- API keys and secrets
- LLM model configuration

## Deployment

### Production Deployment

1. Update environment variables for production
2. Use a production WSGI server like Gunicorn
3. Set up proper logging and monitoring
4. Configure SSL/TLS
5. Use a production PostgreSQL instance

### Scaling

- Use load balancers for horizontal scaling
- Implement connection pooling for database
- Consider Redis for session management
- Monitor memory usage for LLM operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License