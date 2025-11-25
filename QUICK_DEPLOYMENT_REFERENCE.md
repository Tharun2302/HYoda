# ⚡ Quick Deployment Reference Card

## 🎯 One-Page Cheat Sheet

### **Server Info**
- **IP:** 68.183.88.5
- **Specs:** 4 vCPU, 8GB RAM, 160GB Disk
- **OS:** Ubuntu 22.04 with Docker

---

## 📝 Copy-Paste Commands (Run in Order)

### **1. Connect to Server**
```bash
ssh root@68.183.88.5
```

### **2. Update System**
```bash
apt update && apt upgrade -y
```

### **3. Install Docker (if needed)**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
```

### **4. Install Docker Compose (if needed)**
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
```

### **5. Install Ollama**
```bash
curl -fsSL https://ollama.com/install.sh | sh
systemctl start ollama
systemctl enable ollama
```

### **6. Download Models**
```bash
ollama pull alibayram/medgemma:4b
ollama pull nomic-embed-text
```

### **7. Clone Code**
```bash
cd /opt && rm -rf hyoda && git clone https://github.com/Tharun2302/HYoda.git hyoda && cd hyoda
```

### **8. Create .env File**
```bash
cat > .env << 'EOF'
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=alibayram/medgemma:4b
LANGFUSE_ENABLED=true
LANGFUSE_SECRET_KEY=sk-lf-e84d92ef-fbf3-4ecd-b6b2-d910ba7e5b1e
LANGFUSE_PUBLIC_KEY=pk-lf-0ab229bf-b78a-494f-9375-452c3ccae3c0
LANGFUSE_HOST=https://cloud.langfuse.com
MONGODB_URI=mongodb+srv://sudityanimmala_db_user:Arss_2025@healthyoda.idbstnp.mongodb.net/?appName=Healthyoda
MONGODB_DB=Healthyoda
REBUILD_VECTORSTORE=false
VOICE_ENABLED=true
WHISPER_MODEL=tiny.en
PIPER_VOICE=en_US-lessac-medium
ALLOWED_ORIGINS=http://68.183.88.5,http://68.183.88.5:8002,http://localhost:8002
HEALTHBENCH_GRADER_MODEL=alibayram/medgemma:4b
HELM_JUDGE_MODEL=alibayram/medgemma:4b
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
EOF
```

### **9. Deploy**
```bash
chmod +x deploy.sh && ./deploy.sh
```

### **10. Verify**
```bash
docker-compose ps
curl http://localhost:8002/health
docker-compose logs --tail=20 hyoda-app
```

---

## 🔍 Quick Verification Commands

```bash
# Check Ollama
systemctl status ollama
ollama list

# Check Docker
docker --version
docker-compose --version

# Check Containers
docker-compose ps

# Check Logs
docker-compose logs -f hyoda-app

# Test Health
curl http://localhost:8002/health

# Test Ollama from Container
docker-compose exec hyoda-app curl http://host.docker.internal:11434/api/tags
```

---

## 🛠️ Common Fixes

```bash
# Restart Ollama
systemctl restart ollama

# Restart Containers
docker-compose restart

# Rebuild Everything
docker-compose down
docker-compose up -d --build

# View Logs
docker-compose logs -f

# Stop Everything
docker-compose down

# Start Everything
docker-compose up -d
```

---

## 🌐 Access URLs

- **Chatbot:** http://68.183.88.5/index.html
- **Dashboard:** http://68.183.88.5/healthbench/dashboard
- **Health:** http://68.183.88.5/health
- **Direct API:** http://68.183.88.5:8002

---

## ⚠️ Important Notes

1. **Ollama has NO API keys** - it's a local service
2. **First deployment takes 10-15 minutes** (downloading models)
3. **Response time:** 2-5 seconds per message
4. **RAM usage:** ~7GB total (4GB model + 3GB app)

---

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Ollama not found | `systemctl start ollama` |
| Model not found | `ollama pull alibayram/medgemma:4b` |
| Container won't start | `docker-compose logs hyoda-app` |
| Can't access from browser | Check firewall: `ufw allow 80/tcp` |
| Out of memory | Restart: `docker-compose restart` |

---

**Full guide:** See `COMPLETE_DEPLOYMENT_STEPS.md`

