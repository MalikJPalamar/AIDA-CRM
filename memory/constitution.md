# AIDA-CRM Constitution

## Core Principles (FROZEN - DO NOT DELETE)

### CRM Life Cycle
- **Capture** ➜ **Connect** ➜ **Convert** ➜ **Retain**
- Leads, Deals, Comms, Ads, Analytics map one-to-one to life-cycle stages

### UI Heuristics
- TTI ≤ 200 ms; CLS < 0.1; WCAG AA contrast
- Min clicks to task; keyboard-first flows; predictable motion
- Design-tokens single source of truth (spacing, colour, type)

### Autonomy Ladder
- **L1** draft-only ➜ **L5** full auto with human on the loop

### Definition of Done
- Spec Kit phases passed; tests ≥ 85% cov; Lighthouse score ≥ 90
- Guardian reviewer "✅ Principles" on every PR

---

## Project Identity

**AIDA-CRM** – AI-Driven Autonomy CRM (v0.2)

**Purpose**: End-to-end 3C/3B funnel with autonomy levels L1-L5. First product in the Cognitive-Company stack. Spec-Driven, Agentic, Data-Nervous-System architecture.

**Core Architecture**:
- Edge: Stateless FastAPI ingress on Fly.io
- Core: Private VPS with Docker Swarm
- Data Bus: NATS JetStream
- Storage: DuckDB (OLAP), Chroma (vectors), Supabase (transactional)

This constitution serves as the immutable foundation for all development decisions.