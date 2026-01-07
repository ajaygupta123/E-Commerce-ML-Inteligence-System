# Testing Guide for Interviewer

This guide makes it easy to test all requirements from the objective.

## Prerequisites

- Docker & Docker Compose installed
- 8GB+ RAM recommended
- Internet connection (to pull LLM model)

## Quick Start (5 minutes)

### Step 1: Start Services
```bash
# Start all services
docker-compose up -d

# Wait for services to be ready (about 30 seconds)
docker-compose ps
```

### Step 2: Pull LLM Model
```bash
# Pull the Llama 3.2 3B model (about 2GB, takes 2-3 minutes)
docker exec ecommerce-ollama ollama pull llama3.2:3b
```

### Step 3: Seed Database
```bash
# Seed database with sample products
docker exec ecommerce-api python scripts/seed_database.py

# Generate embeddings for RAG
docker exec ecommerce-api python scripts/generate_embeddings.py
```

### Step 4: Run Comprehensive Tests
```bash
# Run the comprehensive test suite
python3 scripts/test_all_requirements.py
```

**That's it!** The script will test everything and generate a report.

## What Gets Tested

### ✅ Requirement 1: Containerized Solution
- Docker health checks
- Service readiness
- All containers running

### ✅ Requirement 2: API Endpoints

#### `/v1/predict_discount`
Tests discount prediction with multiple test cases:
- Electronics products
- Clothing products
- Home & Kitchen products

**Example Request:**
```bash
curl -X POST http://localhost:8000/v1/predict_discount \
  -H "Content-Type: application/json" \
  -d '{
    "actual_price": 100.0,
    "category": "Electronics",
    "rating": 4.5,
    "rating_count": 1000
  }'
```

#### `/v1/answer_question`
Tests RAG-powered question answering:
- Product queries
- Price queries
- Category queries

**Example Request:**
```bash
curl -X POST http://localhost:8000/v1/answer_question \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the cheapest products?"
  }'
```

### ✅ Requirement 3: Regression Metrics

The test script displays:
- **RMSE** (Root Mean Squared Error)
- **MAE** (Mean Absolute Error)
- **R²** (Coefficient of Determination)

**Expected Results:**
- Best Model: CatBoost (Tuned)
- R² = 0.88
- RMSE = 6.89
- MAE = 5.02

Metrics are read from:
- `models/model_comparison.json`
- `models/TRAINING_SUMMARY.md`

### ✅ Requirement 4: RAG Evaluation

The test script evaluates:
- **Grounding Accuracy**: Is the answer supported by retrieved context?
- **Factuality Rate**: Are expected facts present in the answer?
- **Hallucination Rate**: Fraction of unsupported claims
- **Answer Relevance**: Does the answer address the question?

**Test Cases:**
Located in `data/evaluation/rag_test_set.json`

**Expected Metrics:**
- Grounding Score: > 0.90
- Factuality Rate: > 0.85
- Hallucination Rate: < 0.10

## Manual Testing

### Test Individual Endpoints

**1. Health Check:**
```bash
curl http://localhost:8000/health
```

**2. Readiness Check:**
```bash
curl http://localhost:8000/ready
```

**3. Prediction:**
```bash
curl -X POST http://localhost:8000/v1/predict_discount \
  -H "Content-Type: application/json" \
  -d '{
    "actual_price": 100.0,
    "category": "Electronics",
    "rating": 4.5
  }'
```

**4. RAG Question:**
```bash
curl -X POST http://localhost:8000/v1/answer_question \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the cheapest products?"
  }'
```

**5. RAG Evaluation:**
```bash
curl -X POST http://localhost:8000/v1/evaluate_rag \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [
      {
        "question": "What are the cheapest products?",
        "expected_answer": "Products with lowest prices",
        "relevant_products": []
      }
    ]
  }'
```

### Interactive API Documentation

Open in browser:
```bash
open http://localhost:8000/docs
```

This provides:
- Interactive API testing
- Request/response schemas
- Try-it-out functionality

## Test Results

After running `test_all_requirements.py`, you'll get:

1. **Console Output**: Real-time test results with color coding
2. **TEST_REPORT.json**: Detailed JSON report with all metrics

**Report Location:** `TEST_REPORT.json`

**Report Contents:**
- API test results
- Regression metrics (RMSE, MAE, R²)
- RAG evaluation metrics (grounding, factuality)
- Timestamp

## Troubleshooting

### API Not Running
```bash
# Check if containers are running
docker-compose ps

# Start services
docker-compose up -d

# Check logs
docker-compose logs api
```

### LLM Model Not Loaded
```bash
# Check if model is available
docker exec ecommerce-ollama ollama list

# Pull model if missing
docker exec ecommerce-ollama ollama pull llama3.2:3b
```

### Database Not Seeded
```bash
# Seed database
docker exec ecommerce-api python scripts/seed_database.py

# Verify products
docker exec ecommerce-api python -c "
from src.db.postgres import AsyncSessionLocal
from src.db.models.product import Product
import asyncio

async def check():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Product))
        products = result.scalars().all()
        print(f'Products in database: {len(products)}')

asyncio.run(check())
"
```

### Embeddings Not Generated
```bash
# Generate embeddings
docker exec ecommerce-api python scripts/generate_embeddings.py
```

## Expected Test Duration

- Service startup: ~30 seconds
- LLM model pull: ~2-3 minutes (first time only)
- Database seeding: ~10 seconds
- Embedding generation: ~30 seconds
- Test execution: ~1-2 minutes

**Total time: ~5-7 minutes** (including first-time setup)

## Verification Checklist

After running tests, verify:

- [ ] All Docker containers are running
- [ ] Health endpoint returns 200
- [ ] Readiness endpoint shows all services ready
- [ ] Prediction endpoint returns valid discount percentages
- [ ] RAG endpoint returns answers with retrieved products
- [ ] Regression metrics are displayed (RMSE, MAE, R²)
- [ ] RAG metrics are displayed (grounding, factuality)
- [ ] TEST_REPORT.json is generated

## Additional Resources

- **API Documentation**: `docs/API.md`
- **Model Performance**: `models/TRAINING_SUMMARY.md`
- **RAG Evaluation Details**: `docs/RAG_EVALUATION.md`
- **Architecture**: `docs/ARCHITECTURE.md`

---

**For questions or issues, check the main README.md or project documentation.**

