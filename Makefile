.PHONY: up down test lint train seed pull-model logs test-unit test-integration test-security test-all load-test performance-test test-requirements

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f api

test:
	pytest tests/ -v --cov=src

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-security:
	pytest tests/security/ -v

test-all:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/
	mypy src/

eda:
	python3 scripts/eda.py

train:
	python3 scripts/train_models.py

feature-importance:
	python3 scripts/analyze_feature_importance.py

validate:
	python3 scripts/validate_model.py

tune:
	python3 scripts/tune_hyperparameters.py

test-api:
	python3 scripts/test_api.py

test-model:
	python3 scripts/test_model_locally.py

summary:
	python3 scripts/generate_summary_report.py

seed:
	docker exec ecommerce-api python scripts/seed_database.py

pull-model:
	docker exec ecommerce-ollama ollama pull llama3.2:3b

generate-embeddings:
	docker exec ecommerce-api python scripts/generate_embeddings.py

load-test:
	python3 scripts/run_load_tests.py

performance-test:
	python3 scripts/performance_test.py

monitor:
	@python3 scripts/monitor_system.py

monitor-save:
	@python3 scripts/monitor_system.py --save

disable-rate-limit:
	./scripts/disable_rate_limit.sh

enable-rate-limit:
	./scripts/enable_rate_limit.sh

test-requirements:
	@echo "Running comprehensive test suite for interviewer evaluation..."
	@python3 scripts/test_all_requirements.py

setup-and-test:
	@echo "Setting up and testing the system..."
	@echo "1. Starting services..."
	@docker-compose up -d
	@echo "2. Pulling LLM model (this may take a few minutes)..."
	@docker exec ecommerce-ollama ollama pull llama3.2:3b || true
	@echo "3. Seeding database..."
	@docker exec ecommerce-api python scripts/seed_database.py || true
	@echo "4. Generating embeddings..."
	@docker exec ecommerce-api python scripts/generate_embeddings.py || true
	@echo "5. Running comprehensive tests..."
	@python3 scripts/test_all_requirements.py


