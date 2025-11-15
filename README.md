# AI CV Evaluator - Backend Service

An AI-powered backend service that automates initial screening of job applications by evaluating candidate CVs and project reports against job descriptions and case study requirements.

## 🎯 Features

- **PDF Document Upload**: Upload CV and project reports
- **Asynchronous Evaluation**: Non-blocking evaluation pipeline using Celery
- **RAG-Powered Context Retrieval**: Vector database (ChromaDB) for intelligent context matching
- **LLM Chaining**: Multi-stage evaluation using Large Language Models
- **Structured Scoring**: Standardized rubric-based evaluation (1-5 scale)
- **Multiple LLM Support**: OpenAI, Anthropic Claude, OpenRouter, Google Gemini
- **Retry Logic**: Automatic retry with exponential backoff for API failures
- **RESTful API**: Clean, well-documented REST endpoints

## 🏗️ Architecture

![Diagram Alir](images/image.png)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- Redis
- Docker & Docker Compose (optional, recommended)

### Option 1: Docker (Recommended)

1. **Clone and setup**
```bash
git clone <your-repo-url>
cd ai-cv-evaluator
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your LLM API key
```

3. **Start services**
```bash
docker-compose up -d
```

4. **Ingest reference documents**
```bash
# Place your PDF files in data/reference_docs/
docker-compose exec api python scripts/ingest_documents.py
```

5. **Access the API**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower (Celery monitoring): http://localhost:5555

### Option 2: Local Setup

1. **Install dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start PostgreSQL and Redis**
```bash
# Using Docker:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally on your system
```

4. **Ingest reference documents**
```bash
python scripts/ingest_documents.py
```

5. **Start the application**

Terminal 1 - API Server:
```bash
python main.py
```

Terminal 2 - Celery Worker:
```bash
celery -A app.workers.celery_worker worker --loglevel=info
```

Terminal 3 - Celery Flower (optional):
```bash
celery -A app.workers.celery_worker flower --port=5555
```

## 📁 Project Structure

```
ai-cv-evaluator/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── upload.py         # Upload endpoint
│   │       ├── evaluate.py       # Evaluation trigger
│   │       └── result.py         # Result retrieval
│   ├── core/
│   │   ├── config.py            # Configuration
│   │   └── database.py          # Database models
│   ├── models/
│   │   └── schemas.py           # Pydantic schemas
│   ├── services/
│   │   ├── pdf_parser.py        # PDF text extraction
│   │   ├── rag_service.py       # RAG/Vector DB
│   │   ├── llm_service.py       # LLM integration
│   │   └── evaluation_service.py # Evaluation logic
│   └── workers/
│       └── celery_worker.py     # Async task worker
├── data/
│   ├── reference_docs/          # Reference PDFs
│   │   ├── job_description.pdf
│   │   ├── case_study_brief.pdf
│   │   ├── cv_rubric.pdf
│   │   └── project_rubric.pdf
│   └── uploads/                 # User uploads
├── scripts/
│   └── ingest_documents.py      # Document ingestion
├── tests/                       # Test files
├── chroma_db/                   # Vector database
├── logs/                        # Application logs
├── main.py                      # FastAPI app
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# LLM Provider (choose one)
LLM_PROVIDER=openrouter  # openai, anthropic, openrouter, gemini
LLM_MODEL=anthropic/claude-3-haiku  # model name
OPENROUTER_API_KEY=your-key-here

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cv_evaluator

# Redis
REDIS_URL=redis://localhost:6379/0
```

### LLM Provider Setup

**OpenRouter (Recommended - Free Tier Available)**
```bash
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3-haiku
OPENROUTER_API_KEY=sk-or-v1-...
```

**OpenAI**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=sk-...
```

**Anthropic Claude**
```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=sk-ant-...
```

**Google Gemini**
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
GOOGLE_API_KEY=...
```

## 📖 API Documentation

### 1. Upload Documents

**Endpoint**: `POST /api/v1/upload`

Upload CV and project report (both PDF files).

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "cv=@path/to/cv.pdf" \
  -F "project_report=@path/to/report.pdf"
```

**Response**:
```json
{
  "cv": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "john_doe_cv.pdf",
    "document_type": "cv",
    "uploaded_at": "2025-01-15T10:30:00",
    "file_size": 245678
  },
  "project_report": {
    "id": "987fcdeb-51a2-43f1-b789-987654321000",
    "filename": "project_report.pdf",
    "document_type": "project_report",
    "uploaded_at": "2025-01-15T10:30:00",
    "file_size": 456789
  }
}
```

### 2. Start Evaluation

**Endpoint**: `POST /api/v1/evaluate`

Trigger asynchronous evaluation of uploaded documents.

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "cv_id": "123e4567-e89b-12d3-a456-426614174000",
    "project_report_id": "987fcdeb-51a2-43f1-b789-987654321000",
    "job_title": "Backend Engineer"
  }'
```

**Response**:
```json
{
  "id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "status": "queued",
  "message": "Evaluation queued successfully"
}
```

### 3. Get Evaluation Result

**Endpoint**: `GET /api/v1/result/{job_id}`

Retrieve evaluation status and results.

**Request**:
```bash
curl http://localhost:8000/api/v1/result/abc12345-def6-7890-ghij-klmnopqrstuv
```

**Response (Queued/Processing)**:
```json
{
  "id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "status": "processing",
  "result": null,
  "created_at": "2025-01-15T10:30:00",
  "completed_at": null
}
```

**Response (Completed)**:
```json
{
  "id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "status": "completed",
  "result": {
    "cv_match_rate": 0.82,
    "cv_feedback": "Strong backend and cloud experience. Limited AI/LLM integration exposure. Good collaboration indicators.",
    "project_score": 4.5,
    "project_feedback": "Well-implemented prompt chaining and RAG. Could improve error handling robustness. Clear documentation.",
    "overall_summary": "Strong candidate fit for the role. Demonstrates solid backend fundamentals and good understanding of AI integration. Would benefit from deeper hands-on RAG experience. Clear communication skills evident. Recommended for interview.",
    "cv_detailed_scores": {
      "technical_skills_match": 4.5,
      "experience_level": 4.0,
      "relevant_achievements": 3.5,
      "cultural_fit": 4.0
    },
    "project_detailed_scores": {
      "correctness": 4.5,
      "code_quality": 4.0,
      "resilience": 4.0,
      "documentation": 5.0,
      "creativity": 4.0
    }
  },
  "created_at": "2025-01-15T10:30:00",
  "completed_at": "2025-01-15T10:32:30"
}
```

### Additional Endpoints

- `GET /api/v1/results` - List all evaluation jobs
- `GET /api/v1/stats` - Get evaluation statistics
- `GET /health` - Health check

Full API documentation available at: http://localhost:8000/docs

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_evaluation.py
```

## 🎯 Evaluation Pipeline

The system uses a 3-stage LLM chaining approach:

### Stage 1: CV Evaluation
1. Parse CV PDF
2. Retrieve relevant job requirements from vector DB
3. LLM evaluates CV against requirements
4. Output: Match rate (0-1) + detailed scores + feedback

### Stage 2: Project Evaluation
1. Parse project report PDF
2. Retrieve case study requirements from vector DB
3. LLM evaluates project against requirements
4. Output: Score (1-5) + detailed scores + feedback

### Stage 3: Overall Summary
1. Synthesize results from stages 1 & 2
2. LLM generates concise summary
3. Output: 3-5 sentence recommendation

## 📊 Scoring Rubric

### CV Evaluation (Match Rate 0-1)
- **Technical Skills Match** (40%): Backend, databases, APIs, cloud, AI/LLM
- **Experience Level** (25%): Years of experience, project complexity
- **Relevant Achievements** (20%): Impact, scale, measurable outcomes
- **Cultural Fit** (15%): Communication, learning attitude, teamwork

### Project Evaluation (Score 1-5)
- **Correctness** (30%): Prompt design, LLM chaining, RAG implementation
- **Code Quality** (25%): Clean, modular, testable code
- **Resilience** (20%): Error handling, retries, failure management
- **Documentation** (15%): Clear README, setup instructions
- **Creativity** (10%): Bonus features, innovations

## 🛡️ Error Handling

- **Automatic Retries**: Failed LLM calls retry up to 3 times with exponential backoff
- **Timeout Protection**: Tasks have configurable timeouts (default: 5 minutes)
- **Graceful Degradation**: Partial results saved even if pipeline fails mid-way
- **Detailed Logging**: All errors logged with full context
- **Status Tracking**: Real-time job status updates

## 🔐 Security Considerations

- File size limits enforced (10MB default)
- PDF-only uploads
- API rate limiting (production)
- Input validation at all levels
- Secure file storage
- Environment variable protection

## 🚀 Deployment

### Production Checklist

1. **Environment**
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=False`
   - Use strong database passwords
   - Configure proper CORS origins

2. **Database**
   - Use PostgreSQL in production
   - Set up regular backups
   - Configure connection pooling

3. **Monitoring**
   - Set up Celery Flower for task monitoring
   - Configure log aggregation
   - Set up health check endpoints

4. **Scaling**
   - Add more Celery workers for concurrent processing
   - Use load balancer for multiple API instances
   - Configure Redis persistence

### Deploy to Cloud

Example for Heroku/Railway/Render:

```bash
# Set environment variables
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
OPENROUTER_API_KEY=sk-or-...

# Deploy
git push heroku main

# Run document ingestion
heroku run python scripts/ingest_documents.py
```

## 📝 Design Decisions & Trade-offs

### Why ChromaDB?
- **Pros**: Embedded, no separate server, easy setup, good for prototypes
- **Cons**: Not horizontally scalable
- **Alternative**: Qdrant, Weaviate, Pinecone for production scale

### Why Celery?
- **Pros**: Mature, reliable, great for async tasks, good monitoring
- **Cons**: Requires Redis/RabbitMQ
- **Alternative**: RQ (simpler), Cloud Tasks (managed)

### Why Multiple LLM Support?
- **Flexibility**: Different providers for different needs
- **Cost optimization**: Use cheaper models for simple tasks
- **Resilience**: Fallback options if one provider fails

### Temperature = 0.3
- Lower temperature (0.1-0.3) for consistent, deterministic scoring
- Higher values would introduce more randomness

### Chunking Strategy (1000 chars, 200 overlap)
- Balance between context and accuracy
- Larger chunks = more context but slower retrieval
- Overlap ensures no context loss at boundaries

## 🐛 Troubleshooting

### Issue: "Database connection failed"
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection string
echo $DATABASE_URL
```

### Issue: "Celery worker not processing tasks"
```bash
# Check Redis is running
redis-cli ping

# Check Celery worker logs
docker-compose logs celery_worker
```

### Issue: "LLM API timeout"
```bash
# Increase timeout in .env
EVALUATION_TIMEOUT=600

# Check API key is valid
curl https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Issue: "ChromaDB errors"
```bash
# Reset vector database
python scripts/ingest_documents.py --reset
```

## 📈 Performance Tips

1. **Batch Processing**: Process multiple evaluations in parallel with more Celery workers
2. **Caching**: Cache frequent RAG queries (future improvement)
3. **Model Selection**: Use faster models (Haiku, GPT-3.5) for quick evaluations
4. **Database Indexing**: Add indexes on frequently queried columns
5. **Connection Pooling**: Configure SQLAlchemy pool size for high concurrency

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - feel free to use in your projects

## 👥 Contact

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ for automated candidate screening**