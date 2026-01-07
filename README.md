# E-commerce ML Intelligence System

A production-ready intelligent machine learning system for e-commerce data intelligence, featuring predictive discount modeling and RAG-powered question answering.

## 🎯 Overview

This system provides two core capabilities:

1. **Predictive Model**: Forecast product discount percentages using CatBoost
2. **AI Assistant**: RAG-powered Q&A system using self-hosted Llama 3.2 3B

Built with production best practices, comprehensive documentation, and interview-ready architecture decisions.

## 🏗️ Architecture

```
┌─────────────┐
│   FastAPI   │
│     API     │
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
┌──▼──┐ ┌─▼────┐
│PostgreSQL│ │ Qdrant │
│          │ │(Vector)│
└──────────┘ └────────┘
       │
┌──────▼──────┐
│   Ollama    │
│ (Llama 3.2) │
└─────────────┘
```

### Tech Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| API Framework | FastAPI | Async, auto-docs, type hints |
| Relational DB | PostgreSQL 17 Alpine | Industry standard, analytics |
| Vector DB | Qdrant | 15x faster filtered search |
| LLM | Ollama (Llama 3.2 3B) | Self-hosted, optimized |
| ML Model | CatBoost | Better categorical handling |
| Explainability | SHAP | TreeExplainer for CatBoost |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- 8GB+ RAM recommended

#### macOS-Specific Requirements

For local development on macOS, you'll need:

- **Homebrew** (package manager): [Install Homebrew](https://brew.sh/)
- **OpenMP library** (required for LightGBM):
  ```bash
  brew install libomp
  ```

This is required because LightGBM uses OpenMP for parallel processing, and macOS doesn't include it by default.

### Setup

1. **Clone and configure**
```bash
git clone <repository>
cd E-Commerce-ML-Inteligence-System
cp .env.example .env  # Edit if needed
```

2. **Set up Python virtual environment (for local development)**
```bash
# Create virtual environment
python3 -m venv env-ecommerce-ml

# Activate virtual environment
source env-ecommerce-ml/bin/activate  # On macOS/Linux
# or
env-ecommerce-ml\Scripts\activate  # On Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# For model training (requires libomp on macOS - see Prerequisites)
pip install -r requirements-model-prepration.txt
```

3. **Start services**
```bash
make up
# Or: docker-compose up -d
```

4. **Pull LLM model**
```bash
make pull-model
# Or: docker exec ecommerce-ollama ollama pull llama3.2:3b
```

5. **Seed database**
```bash
make seed
# Or: docker exec ecommerce-api python scripts/seed_database.py
```

6. **Access API docs**
```bash
open http://localhost:8000/docs
```

## 📊 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic health check |
| `/ready` | GET | Readiness (DB, model loaded) |
| `/metrics` | GET | Prometheus metrics |
| `/v1/predict_discount` | POST | Predict discount % |
| `/v1/explain` | POST | SHAP explanation |
| `/v1/answer_question` | POST | RAG Q&A |
| `/v1/evaluate_rag` | POST | RAG evaluation metrics |

See [API Documentation](docs/API.md) for details.

## 🧪 Testing

### Unit Tests
```bash
make test
# Or: pytest tests/ -v --cov=src
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Load Tests
```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

## 📈 Model Performance

### Model Comparison

The system trains and compares multiple models:

| Model | Description | Strengths |
|-------|-------------|-----------|
| Random Forest | Ensemble of decision trees | Simple, interpretable baseline |
| LightGBM | Gradient boosting framework | Fast training, good performance |
| XGBoost | Optimized gradient boosting | Robust, widely used |
| CatBoost | Gradient boosting with categorical handling | Best for categorical features |

### Performance Metrics

| Metric | Random Forest | LightGBM | XGBoost | CatBoost |
|--------|---------------|----------|---------|----------|
| RMSE | 19.74 | 17.06 | 19.53 | **14.92** |
| MAE | 16.32 | 13.60 | 16.01 | **11.67** |
| R² | 0.003 | 0.255 | 0.024 | **0.430** |

**Best Model:** CatBoost (Tuned) - R² = 0.88, RMSE = 6.89

**Performance Improvement:**
- Base CatBoost: R² = 0.43, RMSE = 14.92
- Tuned CatBoost: R² = 0.88, RMSE = 6.89
- **Improvement: +104% R², -54% RMSE**

**Top Features:** category (7.24), actual_price (3.91), review_title (3.64)

*See `models/TRAINING_SUMMARY.md` for comprehensive results.*

## 🛠️ Development

### Training Models

1. **Download dataset**
```bash
python scripts/download_dataset.py
# Follow instructions to download from Kaggle
```

2. **Run Exploratory Data Analysis (EDA)**
```bash
python scripts/eda.py
```
This will:
- Analyze dataset structure and quality
- Examine target variable distribution
- Check for missing values and correlations
- Generate summary statistics
- Save analysis results to `data/processed/`

3. **Train models**
```bash
make train
# Or: python scripts/train_models.py
```

This will train and compare multiple models:
- **Random Forest** (baseline - simple, interpretable)
- **LightGBM** (gradient boosting)
- **XGBoost** (gradient boosting)
- **CatBoost** (gradient boosting with categorical handling)

The comparison includes:
- Performance metrics (RMSE, MAE, R²)
- Model comparison report saved to `models/model_comparison.json`
- Best model selection based on R² score

### Generate Embeddings

```bash
make generate-embeddings
# Or: python scripts/generate_embeddings.py
```

### Model Analysis & Improvement

1. **Feature Importance Analysis**
```bash
make feature-importance
# Or: python scripts/analyze_feature_importance.py
```
Generates SHAP-based feature importance analysis and saves to `models/feature_importance.json`

2. **Model Validation**
```bash
make validate
# Or: python scripts/validate_model.py
```
Performs 5-fold cross-validation and holdout validation, saves results to `models/validation_results.json`

3. **Hyperparameter Tuning**
```bash
make tune
# Or: python scripts/tune_hyperparameters.py
```
Uses RandomizedSearchCV to find optimal hyperparameters, saves tuned model to `models/tuned_catboost_model.cbm`

4. **Test API Endpoints**
```bash
make test-api
# Or: python scripts/test_api.py
```
Tests all API endpoints with the trained model (requires API to be running)

5. **Generate Summary Report**
```bash
make summary
# Or: python scripts/generate_summary_report.py
```
Generates a comprehensive summary of all training and evaluation results

### Linting

```bash
make lint
# Or: ruff check src/ && mypy src/
```

## 🔧 Troubleshooting

### LightGBM OpenMP Library Error (macOS)

If you encounter this error when running training scripts:
```
OSError: dlopen(...): Library not loaded: @rpath/libomp.dylib
Reason: tried: '/opt/homebrew/opt/libomp/lib/libomp.dylib' (no such file)
```

**Solution:**
1. Install OpenMP library via Homebrew:
   ```bash
   brew install libomp
   ```
2. Verify installation:
   ```bash
   ls /opt/homebrew/opt/libomp/lib/libomp.dylib
   ```
3. Restart your terminal and reactivate the virtual environment
4. Try running the training script again:
   ```bash
   python scripts/train_models.py
   ```

**Why this happens:**
- LightGBM requires OpenMP for parallel processing
- macOS doesn't include OpenMP by default
- The library must be installed separately via Homebrew

**Alternative Solutions:**
- Use conda instead of pip (conda includes OpenMP automatically)
- Use Docker containers (avoids system dependency issues)

### Module Import Errors

If you get `ModuleNotFoundError` when running scripts:

1. Ensure virtual environment is activated:
   ```bash
   source env-ecommerce-ml/bin/activate
   ```

2. Verify dependencies are installed:
   ```bash
   pip list | grep lightgbm
   pip list | grep catboost
   ```

3. Reinstall dependencies if needed:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-model-prepration.txt
   ```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Architecture Decisions](docs/ARCHITECTURE.md)**: All design decisions with justifications
- **[Model Card](docs/MODEL_CARD.md)**: ML model documentation
- **[LLM Optimization](docs/LLM_OPTIMIZATION.md)**: Ollama tuning details
- **[RAG Evaluation](docs/RAG_EVALUATION.md)**: RAG metrics explanation
- **[API Documentation](docs/API.md)**: Complete API reference

## 🏭 Production Considerations

### Current Implementation
- In-memory cache (abstracted for Redis)
- Local model storage (abstracted for S3/MinIO)
- Basic rate limiting
- Prometheus metrics

### Production Enhancements
- [ ] Redis for distributed caching
- [ ] S3/MinIO for model versioning
- [ ] JWT authentication
- [ ] Request signing
- [ ] DDoS protection
- [ ] Horizontal scaling
- [ ] Model A/B testing
- [ ] Data drift detection

## 📦 Project Structure

```
ecommerce-ml-system/
├── docker/              # Dockerfiles
├── src/
│   ├── api/            # FastAPI application
│   ├── services/       # Business logic
│   ├── ml/             # ML training & inference
│   ├── evaluation/     # RAG evaluation
│   ├── db/             # Database models & repos
│   └── core/           # Config, logging, exceptions
├── tests/              # Test suite
├── scripts/            # Utility scripts
├── docs/               # Documentation
└── models/             # Trained models
```

## 🔧 Configuration

Environment variables (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_HOST`, `QDRANT_PORT`: Qdrant configuration
- `OLLAMA_HOST`, `OLLAMA_PORT`: Ollama configuration
- `LLM_MODEL`: Model name (default: `llama3.2:3b`)
- `MODEL_PATH`: Path to CatBoost model
- `CACHE_TYPE`: Cache backend (default: `memory`)

## 🤝 Contributing

This is an interview assignment project. For questions or improvements:

1. Review architecture decisions in `docs/ARCHITECTURE.md`
2. Follow existing code patterns
3. Add tests for new features
4. Update documentation

## 📝 License

[To be specified]

## 🙏 Acknowledgments

- Amazon Sales Dataset (Kaggle)
- Ollama for LLM hosting
- Qdrant for vector search
- CatBoost for ML modeling

---

**Built for interview showcase** - Demonstrates engineering maturity, ML expertise, and production thinking.

