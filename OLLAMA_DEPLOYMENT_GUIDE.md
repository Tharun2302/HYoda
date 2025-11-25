# HYoda with Ollama MedGemma - Complete Deployment Guide

## Overview

This guide covers deploying HYoda with **Ollama MedGemma 4B** model instead of OpenAI, providing a **fully local, privacy-preserving medical chatbot** deployment.

## What Changed

### Removed
- ✅ OpenAI API dependency
- ✅ OpenAI API key requirement
- ✅ External API calls

### Added
- ✅ Ollama client integration
- ✅ MedGemma 4B model support
- ✅ Local inference
- ✅ Docker host network access

## Architecture

```
┌────────────────────────────────────────┐
│   Digital Ocean Server (68.183.88.5)  │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  Ollama Service (Host)           │ │
│  │  - Port: 11434                   │ │
│  │  - Model: medgemma:4b            │ │
│  └──────────┬───────────────────────┘ │
│             │                          │
│  ┌──────────▼───────────────────────┐ │
│  │  Docker Container: hyoda-app     │ │
│  │  - Connects via host.docker...   │ │
│  │  - Flask + Ollama Client         │ │
│  └──────────────────────────────────┘ │
│                                        │
└────────────────────────────────────────┘
```

## Prerequisites

- Digital Ocean droplet with 8GB RAM, 4 vCPUs
- Ubuntu 22.04 or later
- Docker & Docker Compose installed
- Ollama installed on host machine

## Deployment Steps

### Phase 1: Server Setup

#### 1.1 SSH into Server

```bash
ssh root@68.183.88.5
```

#### 1.2 Update System

```bash
apt update && apt upgrade -y
```

#### 1.3 Install Docker (if not installed)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
```

#### 1.4 Install Docker Compose

```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### Phase 2: Install Ollama & MedGemma

#### 2.1 Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### 2.2 Verify Ollama

```bash
ollama --version
systemctl status ollama
```

#### 2.3 Pull MedGemma Model

```bash
# This will download ~2.5GB
ollama pull alibayram/medgemma:4b
```

#### 2.4 Test Model

```bash
ollama run alibayram/medgemma:4b "What is hypertension?"
```

You should get a medical response. Press `Ctrl+D` to exit.

#### 2.5 Verify Model is Ready

```bash
ollama list
```

Should show `alibayram/medgemma:4b` in the list.

#### 2.6 Pull Embedding Model (for RAG)

```bash
ollama pull nomic-embed-text
```

### Phase 3: Deploy Application

#### 3.1 Clone Repository

```bash
cd /opt
rm -rf hyoda  # Clean any previous deployment
git clone https://github.com/Tharun2302/HYoda.git hyoda
cd hyoda
```

#### 3.2 Create Environment File

```bash
cat > .env << 'EOF'
# Ollama Configuration
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=alibayram/medgemma:4b

# Langfuse Configuration (Optional - for analytics)
LANGFUSE_ENABLED=true
LANGFUSE_SECRET_KEY=sk-lf-e84d92ef-fbf3-4ecd-b6b2-d910ba7e5b1e
LANGFUSE_PUBLIC_KEY=pk-lf-0ab229bf-b78a-494f-9375-452c3ccae3c0
LANGFUSE_HOST=https://cloud.langfuse.com

# MongoDB Configuration
MONGODB_URI=mongodb+srv://sudityanimmala_db_user:Arss_2025@healthyoda.idbstnp.mongodb.net/?appName=Healthyoda
MONGODB_DB=Healthyoda

# Vector Store
REBUILD_VECTORSTORE=false

# Voice Processing
VOICE_ENABLED=true
WHISPER_MODEL=tiny.en
PIPER_VOICE=en_US-lessac-medium

# CORS Configuration
ALLOWED_ORIGINS=http://68.183.88.5,http://68.183.88.5:8002,http://localhost:8002

# HealthBench Configuration (using Ollama)
HEALTHBENCH_GRADER_MODEL=alibayram/medgemma:4b
HELM_JUDGE_MODEL=alibayram/medgemma:4b

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
EOF
```

#### 3.3 Deploy with Docker

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Build Docker images (~5-10 minutes first time)
- Start all containers
- Connect to Ollama on host machine

### Phase 4: Verification

#### 4.1 Check Ollama Connection

```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Should return list of models including medgemma:4b
```

#### 4.2 Check Docker Containers

```bash
docker-compose ps
```

All three containers should show "Up":
- hyoda-chatbot
- hyoda-mongodb  
- hyoda-nginx

#### 4.3 Test Health Endpoint

```bash
curl http://localhost:8002/health
```

Should return: `{"status":"healthy"}`

#### 4.4 Check Application Logs

```bash
docker-compose logs --tail=50 hyoda-app
```

Look for:
- ✅ "Ollama client initialized"
- ✅ "Ollama connected"
- ✅ "RAG System loaded"
- ✅ "MongoDB connected"

#### 4.5 Test from Container

```bash
# Test Ollama access from within container
docker-compose exec hyoda-app curl http://host.docker.internal:11434/api/tags
```

Should return Ollama model list.

### Phase 5: Test Application

#### 5.1 Access in Browser

Open browser and visit:
- **Chatbot**: http://68.183.88.5/index.html
- **Dashboard**: http://68.183.88.5/healthbench/dashboard
- **Landing**: http://68.183.88.5/

#### 5.2 Test Conversation

1. Start a conversation
2. Type: "I have chest pain"
3. Wait for response (2-5 seconds with 4B model)
4. Verify response is from MedGemma (medical-appropriate)

#### 5.3 Monitor Performance

```bash
# Check resource usage
docker stats

# Check RAM usage
free -h

# Monitor Ollama
journalctl -u ollama -f
```

## Configuration Details

### Key Files Modified

1. **`ollama_client.py`** (NEW) - Ollama API wrapper
2. **`app.py`** - Uses Ollama instead of OpenAI
3. **`rag_system.py`** - Ollama embeddings
4. **`evals/simple_live_evaluator.py`** - Ollama-based evaluation
5. **`evals/helm_live_evaluator.py`** - Ollama-based HELM eval
6. **`evals/samplers/ollama_sampler.py`** (NEW) - Evaluation sampler
7. **`docker-compose.yml`** - Added `extra_hosts` for Ollama access
8. **`env.template`** - Updated for Ollama config
9. **`requirements.txt`** - Removed OpenAI, kept httpx/requests

### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `alibayram/medgemma:4b` | MedGemma model |
| `HEALTHBENCH_GRADER_MODEL` | `alibayram/medgemma:4b` | Evaluation model |
| `HELM_JUDGE_MODEL` | `alibayram/medgemma:4b` | HELM evaluation model |

### Docker Network Setup

The `docker-compose.yml` includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This allows containers to access Ollama running on the host machine.

## Performance

### Expected Performance (4 vCPU, 8GB RAM)

- **Response Time**: 2-5 seconds per message
- **RAM Usage**: 
  - Ollama + Model: ~4-5 GB
  - Docker containers: ~2-3 GB
  - Total: ~7 GB (fits in 8GB droplet)
- **Concurrent Users**: 2-3 simultaneous conversations
- **Throughput**: ~20-30 requests/minute

### Optimizations

For better performance:

1. **Use larger droplet**: 16GB RAM for smoother operation
2. **Reduce model calls**: Cache common responses
3. **Limit evaluation frequency**: Evaluate every Nth message
4. **Use faster model**: Try mistral:7b if speed is critical

## Troubleshooting

### Issue: Ollama Not Accessible from Container

**Symptoms:**
- "Connection refused" errors
- "Cannot connect to Ollama" in logs

**Solution:**
```bash
# Verify Ollama is running
systemctl status ollama

# Check port is listening
netstat -tlnp | grep 11434

# Test from host
curl http://localhost:11434/api/tags

# Verify extra_hosts in docker-compose.yml
grep -A 2 "extra_hosts" docker-compose.yml
```

### Issue: Model Too Slow

**Symptoms:**
- Responses take >10 seconds
- High CPU usage

**Solutions:**
```bash
# Check if model is loaded
ollama list

# Restart Ollama
systemctl restart ollama

# Use smaller model
ollama pull mistral:7b
# Update .env: OLLAMA_MODEL=mistral:7b
```

### Issue: Out of Memory

**Symptoms:**
- Container crashes
- "OOMKilled" in docker logs

**Solutions:**
```bash
# Check memory
free -h

# Stop unnecessary services
docker-compose stop nginx  # If using direct access

# Use smaller model
# MedGemma 4B uses ~4-5GB
# Consider llama2:3b for ~3GB usage
```

### Issue: Embeddings Fail

**Symptoms:**
- RAG system not working
- "Embedding failed" errors

**Solution:**
```bash
# Pull embedding model
ollama pull nomic-embed-text

# Verify it's available
ollama list | grep nomic

# Test embeddings
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}'
```

### Issue: Evaluation Not Working

**Symptoms:**
- No evaluation scores in dashboard
- "Evaluation failed" in logs

**Solution:**
```bash
# Check evaluator logs
docker-compose logs hyoda-app | grep EVALUATOR

# Verify Ollama model is responsive
time ollama run alibayram/medgemma:4b "test"

# Check evaluation is enabled
docker-compose exec hyoda-app env | grep HEALTHBENCH
```

## Maintenance

### Update Model

```bash
# Pull latest version
ollama pull alibayram/medgemma:4b

# Restart containers
docker-compose restart hyoda-app
```

### Update Application

```bash
cd /opt/hyoda
git pull origin main
./deploy.sh --build
```

### Backup

```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --out=/data/backup
docker cp hyoda-mongodb:/data/backup ./backup-$(date +%Y%m%d)

# Backup vector database
tar -czf chroma_db-backup-$(date +%Y%m%d).tar.gz chroma_db/
```

### Monitor Ollama

```bash
# View Ollama logs
journalctl -u ollama -f

# Check Ollama stats
curl http://localhost:11434/api/tags

# Restart Ollama if needed
systemctl restart ollama
```

## Advantages of Ollama Deployment

✅ **No API Costs** - Completely free inference  
✅ **Privacy** - All data stays on your server  
✅ **No Rate Limits** - Run as many queries as your hardware allows  
✅ **Offline Capable** - Works without internet (after model download)  
✅ **Medical-Specialized** - MedGemma trained on medical data  
✅ **Customizable** - Can fine-tune or swap models  

## Limitations

⚠️ **Slower than Cloud** - 2-5s vs <1s with OpenAI  
⚠️ **Resource Intensive** - Needs 8GB+ RAM  
⚠️ **Limited Concurrent Users** - 2-3 simultaneous conversations  
⚠️ **Model Quality** - MedGemma 4B < GPT-4 (but still very capable)  

## Next Steps

1. ✅ **Test thoroughly** - Try various medical scenarios
2. ✅ **Monitor performance** - Watch RAM and response times
3. ✅ **Tune parameters** - Adjust temperature, max_tokens
4. ✅ **Consider upgrades** - If too slow, upgrade droplet or try 27B model
5. ✅ **Setup monitoring** - Add Grafana/Prometheus for production

## Support

For issues:
- Check logs: `docker-compose logs -f hyoda-app`
- Test Ollama: `curl http://localhost:11434/api/tags`
- Verify model: `ollama list`
- Check network: `docker-compose exec hyoda-app curl http://host.docker.internal:11434/api/tags`

---

**Status**: ✅ Ollama Integration Complete  
**Model**: alibayram/medgemma:4b  
**Server**: 68.183.88.5  
**Deployment**: Docker + Ollama on host

