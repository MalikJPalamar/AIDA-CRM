# AIDA-CRM – AI-Driven Autonomy CRM

> **End-to-end 3C/3B funnel with autonomy levels L1-L5**
> First product in the Cognitive-Company stack.
> Spec-Driven, Agentic, Data-Nervous-System architecture.

## 🏗️ Architecture

**Edge Layer (Fly.io)**
- Stateless FastAPI ingress
- Global distribution for low latency
- Authentication and rate limiting

**Core Layer (Private VPS)**
- Docker Swarm orchestration
- Business logic and data processing
- Event-driven microservices

**Data Layer**
- **NATS JetStream**: Event streaming and message bus
- **Supabase**: Transactional database
- **DuckDB**: Analytics and OLAP workloads
- **Chroma**: Vector database for AI features

## 🔄 CRM Life-Cycle

### 1. Capture ➜ 2. Connect ➜ 3. Convert ➜ 4. Retain

- **Capture**: Multi-channel lead acquisition
- **Connect**: AI-powered personalized outreach
- **Convert**: Automated deal progression
- **Retain**: Proactive customer success

## 🤖 Autonomy Levels

- **L1**: Draft-only (human executes)
- **L2**: Assisted (human approves)
- **L3**: Supervised (human oversight)
- **L4**: Delegated (bounded automation)
- **L5**: Autonomous (human-on-the-loop)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ for UI development
- Python 3.11+ for API development

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd aida-crm

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Start core services
docker-compose up -d

# Install UI dependencies
cd ui && npm install

# Start development servers
npm run dev  # UI on http://localhost:3000
# API runs on http://localhost:8000
```

### Environment Variables

See `.env.example` for required configuration. Key variables:

- `OPENROUTER_API_KEY`: For AI/LLM features
- `SUPABASE_URL` & `SUPABASE_SERVICE_ROLE`: Database access
- `NATS_URL`: Event streaming connection

## 📊 Monitoring

- **Prometheus**: Metrics collection at `:9090`
- **Grafana**: Dashboards at `:3000`
- **NATS Monitor**: Stream health at `:8222`

## 🧪 Testing

```bash
# Run all tests
pytest tests/ --cov=.

# UI tests
cd ui && npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📚 Documentation

- [`memory/constitution.md`](memory/constitution.md): Core principles (immutable)
- [`specs/aida-crm.md`](specs/aida-crm.md): System specification
- [`plans/arch-edge-core.md`](plans/arch-edge-core.md): Architecture details
- [`ui/Playbook.md`](ui/Playbook.md): UI component guidelines

## 🎯 Definition of Done

- ✅ Spec Kit phases passed
- ✅ Tests ≥ 85% coverage
- ✅ Lighthouse score ≥ 90
- ✅ Guardian reviewer "✅ Principles" on every PR

## 🛠️ Tech Stack

**Frontend**: Next.js, TypeScript, shadcn/ui, Tailwind CSS
**Backend**: FastAPI, Python, Pydantic
**Data**: Supabase, DuckDB, Chroma, NATS
**AI/ML**: OpenRouter (Kimi-K2), Vector embeddings
**Infra**: Docker Swarm, Fly.io, Prometheus, Grafana

---

**License**: MIT
**Version**: 0.2
**Status**: In Development