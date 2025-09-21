# AIDA-CRM Quick Deployment Guide 🚀

## ✅ FIXED: Production Ready for Hostinger

All issues resolved:
- ✅ Port conflicts fixed
- ✅ OpenRouter API key configured
- ✅ Docker compose streamlined
- ✅ Environment variables set

## 🏁 Deploy Now (2 minutes)

### 1. Create Environment File
```bash
# Copy this exact content to .env file
cat > .env << 'EOF'
# AIDA-CRM Production Environment Configuration

# AI Service (OpenRouter)
OPENROUTER_API_KEY=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
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=moonshotai/kimi-k2

# Security
SECRET_KEY=aida_crm_production_secret_2024_super_secure
JWT_SECRET=aida_jwt_secret_2024_production_ready
CHROMA_AUTH_TOKEN=aida_chroma_token_2024

# Database
POSTGRES_PASSWORD=aida_secure_db_password_2024
POSTGRES_USER=postgres
POSTGRES_DB=aida_crm

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Optional: Monitoring
GRAFANA_PASSWORD=aida_admin_2024
EOF
```

### 2. Stop Any Conflicting Services
```bash
# Stop and remove any existing containers
docker-compose down
docker system prune -f
```

### 3. Deploy AIDA-CRM
```bash
# Pull latest changes
git pull origin master

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Verify Deployment
```bash
# Wait 30 seconds, then test
sleep 30

# Test main API
curl http://localhost:8080/health

# Expected response:
# {"status":"success","message":"Edge API is healthy",...}
```

## 🎯 Access Your CRM

Once deployed successfully:

- **🌐 Main CRM API**: http://your-hostinger-ip:8080
- **📊 Dashboard**: http://your-hostinger-ip:3000
- **⚡ Core API**: http://your-hostinger-ip:8000
- **📡 NATS Monitor**: http://your-hostinger-ip:8222

## 🔧 Service Status Check

```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs edge
docker-compose logs core
```

## 🎉 Success Indicators

You should see:
- ✅ 6 containers running (nats, postgres, chroma, core, edge, ui)
- ✅ All health checks passing
- ✅ API responding on port 8080
- ✅ No port conflict errors

## 🚨 If Issues Occur

```bash
# Check for port conflicts
netstat -tulpn | grep ":8001\|:8000\|:8080"

# Restart specific service
docker-compose restart core

# View detailed logs
docker-compose logs --tail=50 core
```

## 🎯 Production Notes

- **Database**: PostgreSQL with persistent storage
- **Vector DB**: ChromaDB for AI embeddings
- **Message Bus**: NATS JetStream for events
- **Security**: JWT authentication enabled
- **Monitoring**: Health checks on all services
- **Restart Policy**: Auto-restart on failure

---

**🤖 AIDA-CRM v0.2 - Ready for Enterprise Use**
*Complete L1-L5 Autonomy • AI-Driven CRM • Production Deployed*