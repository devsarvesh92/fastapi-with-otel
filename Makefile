# FastAPI OpenTelemetry Observability Stack
# Makefile for easy development and deployment

.PHONY: help setup up down restart run test logs status clean health install check-uv

# Default target
help: ## Show this help message
	@echo "FastAPI OpenTelemetry Observability Stack"
	@echo "==========================================="
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $1, $2}' $(MAKEFILE_LIST)

# Check if uv is installed
check-uv:
	@which uv > /dev/null || (echo "❌ Error: uv is not installed. Please install uv first:" && \
	echo "  macOS: brew install uv" && \
	echo "  Linux: curl -LsSf https://astral.sh/uv/install.sh | sh" && \
	echo "  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"" && \
	echo "" && \
	echo "Or visit: https://docs.astral.sh/uv/getting-started/installation/" && \
	exit 1)

# Setup and Installation
setup: check-uv ## Create directories and install Python dependencies with uv
	@echo "🏗️ Setting up project structure..."
	mkdir -p config/provisioning/datasources
	mkdir -p dashboards
	@echo "📦 Installing Python dependencies with uv..."
	uv venv
	uv pip install -r requirements.txt
	@echo "✅ Setup complete!"
	@echo "💡 To activate the virtual environment, run:"
	@echo "   source .venv/bin/activate  # Linux/macOS"
	@echo "   .venv\\Scripts\\activate    # Windows"

install: setup ## Alias for setup

sync: check-uv ## Sync dependencies with uv
	@echo "🔄 Syncing dependencies with uv..."
	uv pip sync requirements.txt
	@echo "✅ Dependencies synced!"

# Docker Services Management
up: ## Start all infrastructure services
	@echo "🚀 Starting observability stack..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	sleep 30
	@make health
	@echo "✅ All services started!"
	@echo ""
	@echo "🌐 Access URLs:"
	@echo "  FastAPI:    http://localhost:8000"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Tempo:      http://localhost:3200"

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped!"

restart: down up ## Restart all services

# Application Management
run: check-uv ## Start FastAPI application with uv
	@echo "🚀 Starting FastAPI application with uv..."
	@echo "📊 Telemetry will be sent to OTEL Collector"
	@if [ -f .venv/bin/python ]; then \
		echo "🐍 Using virtual environment"; \
		.venv/bin/python app/main.py; \
	else \
		echo "🐍 Using uv run"; \
		uv run app/main.py; \
	fi

dev: check-uv ## Start FastAPI in development mode with auto-reload using uv
	@echo "🔧 Starting FastAPI in development mode with uv..."
	@if [ -f .venv/bin/uvicorn ]; then \
		echo "🐍 Using virtual environment"; \
		.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "🐍 Using uv run"; \
		uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	fi

# Python Environment Management
venv: check-uv ## Create virtual environment with uv
	@echo "🐍 Creating virtual environment with uv..."
	uv venv
	@echo "✅ Virtual environment created!"
	@echo "💡 To activate: source .venv/bin/activate"

venv-info: ## Show virtual environment information
	@echo "🐍 Python Environment Information:"
	@if [ -f .venv/bin/python ]; then \
		echo "✅ Virtual environment exists"; \
		echo "📍 Location: .venv/"; \
		echo "🐍 Python version: $(uv run python --version)"; \
		echo "📦 Installed packages:"; \
		uv pip list; \
	else \
		echo "❌ Virtual environment not found"; \
		echo "💡 Run 'make venv' to create one"; \
	fi

clean-venv: ## Remove virtual environment
	@echo "🧹 Removing virtual environment..."
	rm -rf .venv
	@echo "✅ Virtual environment removed!"

# Testing and Data Generation
test: ## Generate test requests to create sample data
	@echo "🧪 Generating test data..."
	@echo "📊 Making various requests to generate telemetry..."
	curl -s http://localhost:8000/ > /dev/null
	curl -s http://localhost:8000/users/123 > /dev/null
	curl -s http://localhost:8000/users/1001 > /dev/null
	curl -s http://localhost:8000/health > /dev/null
	curl -s -X POST http://localhost:8000/orders -H "Content-Type: application/json" -d '{"amount": 99.99}' > /dev/null
	curl -s http://localhost:8000/slow > /dev/null
	curl -s http://localhost:8000/error > /dev/null || true
	curl -s http://localhost:8000/random > /dev/null || true
	curl -s http://localhost:8000/random > /dev/null || true
	@echo "✅ Test data generated!"
	@echo "📈 Check Grafana at http://localhost:3000"

load-test: ## Generate high volume of requests for load testing
	@echo "⚡ Running load test..."
	@for i in $(seq 1 50); do \
		curl -s http://localhost:8000/users/$i > /dev/null & \
	done
	@wait
	@echo "✅ Load test completed!"

# Monitoring and Debugging
logs: ## View logs from all services
	docker-compose logs -f

logs-collector: ## View OTEL Collector logs
	docker logs -f otel-collector

logs-grafana: ## View Grafana logs
	docker logs -f grafana

logs-prometheus: ## View Prometheus logs
	docker logs -f prometheus

logs-tempo: ## View Tempo logs
	docker logs -f tempo

logs-loki: ## View Loki logs
	docker logs -f loki

status: ## Check status of all services
	@echo "🔍 Checking service status..."
	@echo ""
	@echo "📊 Container Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(otel-collector|prometheus|tempo|loki|grafana)"
	@echo ""
	@echo "🏥 Health Checks:"
	@$(MAKE) health

health: ## Check health of all services
	@echo "Checking OTEL Collector..." && curl -s http://localhost:13133 > /dev/null && echo "✅ OTEL Collector: OK" || echo "❌ OTEL Collector: FAIL"
	@echo "Checking Prometheus..." && curl -s http://localhost:9090/-/ready > /dev/null && echo "✅ Prometheus: OK" || echo "❌ Prometheus: FAIL"
	@echo "Checking Tempo..." && curl -s http://localhost:3200/ready > /dev/null && echo "✅ Tempo: OK" || echo "❌ Tempo: FAIL"
	@echo "Checking Loki..." && curl -s http://localhost:3100/ready > /dev/null && echo "✅ Loki: OK" || echo "❌ Loki: FAIL"
	@echo "Checking Grafana..." && curl -s http://localhost:3000/api/health > /dev/null && echo "✅ Grafana: OK" || echo "❌ Grafana: FAIL"

# Data Exploration
metrics: ## Query sample metrics from Prometheus
	@echo "📊 Sample Prometheus Metrics:"
	@echo ""
	@echo "HTTP Request Rate (last 5m):"
	@curl -s "http://localhost:9090/api/v1/query?query=rate(fastapi_http_requests_custom_total[5m])" | jq -r '.data.result[] | "\(.metric.endpoint) \(.metric.method): \(.value[1])"' 2>/dev/null || echo "No data yet - generate some with 'make test'"

traces: ## Search for traces in Tempo
	@echo "🔍 Sample Traces from Tempo:"
	@curl -s "http://localhost:3200/api/search?limit=5" | jq -r '.traces[]? | "Trace: \(.traceID) - \(.rootTraceName) (\(.durationMs)ms)"' 2>/dev/null || echo "No traces yet - generate some with 'make test'"

explore: ## Open exploration URLs
	@echo "🌐 Opening exploration interfaces..."
	@echo "Opening Grafana Explore..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:3000/explore')" 2>/dev/null || echo "Visit http://localhost:3000/explore"
	@echo "Opening Prometheus..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:9090')" 2>/dev/null || echo "Visit http://localhost:9090"

# Cleanup
clean: ## Remove all containers, volumes, and networks
	@echo "🧹 Cleaning up everything..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete!"

clean-data: ## Remove only data volumes (keep containers)
	@echo "🗑️ Removing data volumes..."
	docker-compose down
	docker volume rm $(docker volume ls -q | grep -E "(prometheus_data|grafana_data|tempo_data|loki_data)") 2>/dev/null || true
	@echo "✅ Data volumes removed!"

clean-all: clean clean-venv ## Remove everything including virtual environment
	@echo "🧹 Complete cleanup including virtual environment!"

# Development Helpers
shell-collector: ## Open shell in OTEL Collector container
	docker exec -it otel-collector sh

shell-grafana: ## Open shell in Grafana container
	docker exec -it grafana bash

config-check: ## Validate configuration files
	@echo "🔧 Checking configuration files..."
	@echo "Checking docker-compose.yml..."
	@docker-compose config > /dev/null && echo "✅ docker-compose.yml: Valid" || echo "❌ docker-compose.yml: Invalid"
	@echo "Checking YAML files..."
	@for file in config/*.yaml; do \
		python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null && echo "✅ $file: Valid" || echo "❌ $file: Invalid"; \
	done

# UV-specific commands
uv-check: check-uv ## Check uv installation and version
	@echo "🔍 UV Information:"
	@echo "Version: $(uv --version)"
	@echo "Location: $(which uv)"

uv-update: check-uv ## Update uv to latest version
	@echo "⬆️ Updating uv..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "📦 Updating via Homebrew..."; \
		brew upgrade uv; \
	else \
		echo "📦 Updating via self-update..."; \
		uv self update; \
	fi
	@echo "✅ UV updated to: $(uv --version)"

# Documentation
ports: ## Show all used ports
	@echo "📡 Port Mapping:"
	@echo "  8000  - FastAPI Application"
	@echo "  3000  - Grafana Dashboard"
	@echo "  9090  - Prometheus"
	@echo "  3200  - Tempo"
	@echo "  3100  - Loki"
	@echo "  4317  - OTEL Collector (gRPC)"
	@echo "  4318  - OTEL Collector (HTTP)"
	@echo "  8889  - OTEL Collector (Prometheus metrics)"
	@echo "  13133 - OTEL Collector (Health check)"

urls: ## Show all service URLs
	@echo "🌐 Service URLs:"
	@echo "  FastAPI:          http://localhost:8000"
	@echo "  FastAPI Docs:     http://localhost:8000/docs"
	@echo "  Grafana:          http://localhost:3000 (admin/admin)"
	@echo "  Prometheus:       http://localhost:9090"
	@echo "  Tempo:            http://localhost:3200"
	@echo "  Loki:             http://localhost:3100"
	@echo "  Collector Health: http://localhost:13133"

requirements: ## Show UV and other requirements
	@echo "📋 Requirements:"
	@echo "  ✅ uv (Python package manager)"
	@echo "  ✅ Docker & Docker Compose"
	@echo "  ✅ curl (for testing)"
	@echo "  ✅ jq (for JSON parsing)"
	@echo ""
	@echo "📦 Install uv:"
	@echo "  macOS:   brew install uv"
	@echo "  Linux:   curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""

# Quick Start
quickstart: setup up ## Complete setup and start (one command)
	@echo ""
	@echo "🎉 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Activate virtual env:   source .venv/bin/activate"
	@echo "2. Start your FastAPI app: make run"
	@echo "3. Generate test data:     make test"
	@echo "4. Explore dashboards:     make explore"

# CI/CD Helpers
ci-test: up test health ## Run tests for CI/CD pipeline
	@echo "🤖 CI/CD test completed successfully!"

# Advanced Operations
backup: ## Backup Grafana dashboards and data
	@echo "💾 Creating backup..."
	@mkdir -p backup
	@docker exec grafana tar czf - /var/lib/grafana > backup/grafana-$(shell date +%Y%m%d-%H%M%S).tar.gz
	@echo "✅ Backup created in backup/ directory"

restore: ## Restore Grafana from backup (specify BACKUP_FILE)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "❌ Please specify BACKUP_FILE=path/to/backup.tar.gz"; exit 1; fi
	@echo "🔄 Restoring from $(BACKUP_FILE)..."
	@docker exec -i grafana tar xzf - -C / < $(BACKUP_FILE)
	@docker restart grafana
	@echo "✅ Restore completed!"

# Docker Services Management
up: ## Start all infrastructure services
	@echo "🚀 Starting observability stack..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	sleep 30
	@make health
	@echo "✅ All services started!"
	@echo ""
	@echo "🌐 Access URLs:"
	@echo "  FastAPI:    http://localhost:8000"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Tempo:      http://localhost:3200"

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped!"

restart: down up ## Restart all services

# Application Management
run: ## Start FastAPI application
	@echo "🚀 Starting FastAPI application..."
	@echo "📊 Telemetry will be sent to OTEL Collector"
	python app/main.py

dev: ## Start FastAPI in development mode with auto-reload
	@echo "🔧 Starting FastAPI in development mode..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing and Data Generation
test: ## Generate test requests to create sample data
	@echo "🧪 Generating test data..."
	@echo "📊 Making various requests to generate telemetry..."
	curl -s http://localhost:8000/ > /dev/null
	curl -s http://localhost:8000/users/123 > /dev/null
	curl -s http://localhost:8000/users/1001 > /dev/null
	curl -s http://localhost:8000/health > /dev/null
	curl -s -X POST http://localhost:8000/orders -H "Content-Type: application/json" -d '{"amount": 99.99}' > /dev/null
	curl -s http://localhost:8000/slow > /dev/null
	curl -s http://localhost:8000/error > /dev/null || true
	curl -s http://localhost:8000/random > /dev/null || true
	curl -s http://localhost:8000/random > /dev/null || true
	@echo "✅ Test data generated!"
	@echo "📈 Check Grafana at http://localhost:3000"

load-test: ## Generate high volume of requests for load testing
	@echo "⚡ Running load test..."
	@for i in $$(seq 1 50); do \
		curl -s http://localhost:8000/users/$$i > /dev/null & \
	done
	@wait
	@echo "✅ Load test completed!"

# Monitoring and Debugging
logs: ## View logs from all services
	docker-compose logs -f

logs-collector: ## View OTEL Collector logs
	docker logs -f otel-collector

logs-grafana: ## View Grafana logs
	docker logs -f grafana

logs-prometheus: ## View Prometheus logs
	docker logs -f prometheus

logs-tempo: ## View Tempo logs
	docker logs -f tempo

logs-loki: ## View Loki logs
	docker logs -f loki

status: ## Check status of all services
	@echo "🔍 Checking service status..."
	@echo ""
	@echo "📊 Container Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(otel-collector|prometheus|tempo|loki|grafana)"
	@echo ""
	@echo "🏥 Health Checks:"
	@$(MAKE) health

health: ## Check health of all services
	@echo "Checking OTEL Collector..." && curl -s http://localhost:13133 > /dev/null && echo "✅ OTEL Collector: OK" || echo "❌ OTEL Collector: FAIL"
	@echo "Checking Prometheus..." && curl -s http://localhost:9090/-/ready > /dev/null && echo "✅ Prometheus: OK" || echo "❌ Prometheus: FAIL"
	@echo "Checking Tempo..." && curl -s http://localhost:3200/ready > /dev/null && echo "✅ Tempo: OK" || echo "❌ Tempo: FAIL"
	@echo "Checking Loki..." && curl -s http://localhost:3100/ready > /dev/null && echo "✅ Loki: OK" || echo "❌ Loki: FAIL"
	@echo "Checking Grafana..." && curl -s http://localhost:3000/api/health > /dev/null && echo "✅ Grafana: OK" || echo "❌ Grafana: FAIL"

# Data Exploration
metrics: ## Query sample metrics from Prometheus
	@echo "📊 Sample Prometheus Metrics:"
	@echo ""
	@echo "HTTP Request Rate (last 5m):"
	@curl -s "http://localhost:9090/api/v1/query?query=rate(fastapi_http_requests_custom_total[5m])" | jq -r '.data.result[] | "\(.metric.endpoint) \(.metric.method): \(.value[1])"' 2>/dev/null || echo "No data yet - generate some with 'make test'"

traces: ## Search for traces in Tempo
	@echo "🔍 Sample Traces from Tempo:"
	@curl -s "http://localhost:3200/api/search?limit=5" | jq -r '.traces[]? | "Trace: \(.traceID) - \(.rootTraceName) (\(.durationMs)ms)"' 2>/dev/null || echo "No traces yet - generate some with 'make test'"

explore: ## Open exploration URLs
	@echo "🌐 Opening exploration interfaces..."
	@echo "Opening Grafana Explore..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:3000/explore')" 2>/dev/null || echo "Visit http://localhost:3000/explore"
	@echo "Opening Prometheus..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:9090')" 2>/dev/null || echo "Visit http://localhost:9090"

# Cleanup
clean: ## Remove all containers, volumes, and networks
	@echo "🧹 Cleaning up everything..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete!"

clean-data: ## Remove only data volumes (keep containers)
	@echo "🗑️ Removing data volumes..."
	docker-compose down
	docker volume rm $$(docker volume ls -q | grep -E "(prometheus_data|grafana_data|tempo_data|loki_data)") 2>/dev/null || true
	@echo "✅ Data volumes removed!"

# Development Helpers
shell-collector: ## Open shell in OTEL Collector container
	docker exec -it otel-collector sh

shell-grafana: ## Open shell in Grafana container
	docker exec -it grafana bash

config-check: ## Validate configuration files
	@echo "🔧 Checking configuration files..."
	@echo "Checking docker-compose.yml..."
	@docker-compose config > /dev/null && echo "✅ docker-compose.yml: Valid" || echo "❌ docker-compose.yml: Invalid"
	@echo "Checking YAML files..."
	@for file in config/*.yaml; do \
		python -c "import yaml; yaml.safe_load(open('$$file'))" 2>/dev/null && echo "✅ $$file: Valid" || echo "❌ $$file: Invalid"; \
	done

# Documentation
ports: ## Show all used ports
	@echo "📡 Port Mapping:"
	@echo "  8000  - FastAPI Application"
	@echo "  3000  - Grafana Dashboard"
	@echo "  9090  - Prometheus"
	@echo "  3200  - Tempo"
	@echo "  3100  - Loki"
	@echo "  4317  - OTEL Collector (gRPC)"
	@echo "  4318  - OTEL Collector (HTTP)"
	@echo "  8889  - OTEL Collector (Prometheus metrics)"
	@echo "  13133 - OTEL Collector (Health check)"

urls: ## Show all service URLs
	@echo "🌐 Service URLs:"
	@echo "  FastAPI:          http://localhost:8000"
	@echo "  FastAPI Docs:     http://localhost:8000/docs"
	@echo "  Grafana:          http://localhost:3000 (admin/admin)"
	@echo "  Prometheus:       http://localhost:9090"
	@echo "  Tempo:            http://localhost:3200"
	@echo "  Loki:             http://localhost:3100"
	@echo "  Collector Health: http://localhost:13133"

# Quick Start
quickstart: setup up ## Complete setup and start (one command)
	@echo ""
	@echo "🎉 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Start your FastAPI app: make run"
	@echo "2. Generate test data:     make test"
	@echo "3. Explore dashboards:     make explore"

# CI/CD Helpers
ci-test: up test health ## Run tests for CI/CD pipeline
	@echo "🤖 CI/CD test completed successfully!"

# Advanced Operations
backup: ## Backup Grafana dashboards and data
	@echo "💾 Creating backup..."
	@mkdir -p backup
	@docker exec grafana tar czf - /var/lib/grafana > backup/grafana-$(shell date +%Y%m%d-%H%M%S).tar.gz
	@echo "✅ Backup created in backup/ directory"

restore: ## Restore Grafana from backup (specify BACKUP_FILE)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "❌ Please specify BACKUP_FILE=path/to/backup.tar.gz"; exit 1; fi
	@echo "🔄 Restoring from $(BACKUP_FILE)..."
	@docker exec -i grafana tar xzf - -C / < $(BACKUP_FILE)
	@docker restart grafana
	@echo "✅ Restore completed!"