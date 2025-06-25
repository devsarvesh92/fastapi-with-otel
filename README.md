# FastAPI OpenTelemetry Observability Stack

Complete observability solution with metrics, traces, and logs.

## Architecture
```
FastAPI → OTEL Collector → Prometheus/Tempo/Loki → Grafana
```

## Quick Start

```bash
# Setup
make setup

# Start infrastructure
make up

# Run app
make run

# Generate test data
make test
```

## Access URLs

- **FastAPI**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   └── otel_setup.py        # OTEL configuration
├── config/                  # All YAML configs
├── docker-compose.yml       
├── requirements.txt         
└── Makefile                
```

## Key Commands

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies |
| `make up` | Start infrastructure |
| `make run` | Start FastAPI app |
| `make test` | Generate test data |
| `make status` | Check health |
| `make down` | Stop services |
| `make clean` | Clean up |

## Requirements

- **uv** (Python package manager)
- **Docker** and **Docker Compose**

Install uv:
```bash
# macOS
brew install uv

# Linux/Windows
curl -LsSf https://astral.sh/uv/install.sh | sh
```