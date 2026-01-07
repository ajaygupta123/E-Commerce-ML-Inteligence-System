.PHONY: up down test lint train seed pull-model logs test-unit test-integration test-security test-all load-test performance-test

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
	python scripts/eda.py

train:
	python scripts/train_models.py

feature-importance:
	python scripts/analyze_feature_importance.py

validate:
	python scripts/validate_model.py

tune:
	python scripts/tune_hyperparameters.py

test-api:
	python scripts/test_api.py

test-model:
	python scripts/test_model_locally.py

summary:
	python scripts/generate_summary_report.py

seed:
	docker exec ecommerce-api python scripts/seed_database.py

pull-model:
	docker exec ecommerce-ollama ollama pull llama3.2:3b

generate-embeddings:
	docker exec ecommerce-api python scripts/generate_embeddings.py

load-test:
	python scripts/run_load_tests.py

performance-test:
	python scripts/performance_test.py

monitor:
	@python scripts/monitor_system.py

monitor-save:
	@python scripts/monitor_system.py --save

disable-rate-limit:
	./scripts/disable_rate_limit.sh

enable-rate-limit:
	./scripts/enable_rate_limit.sh


