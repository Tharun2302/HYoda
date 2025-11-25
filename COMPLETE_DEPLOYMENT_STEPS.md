# 🚀 Complete Step-by-Step Deployment Guide for Beginners

## ⚠️ IMPORTANT: About Ollama and "Keys"

**Ollama does NOT use API keys!** 

- Ollama is a **local service** that runs on your server
- It's like a local web server - you just connect to it via HTTP
- No authentication needed, no keys required
- The "endpoint" is just the URL: `http://localhost:11434` (on server) or `http://host.docker.internal:11434` (from Docker)
- You CAN access Ollama from your local machine if you expose it, but it's meant to run on the server

---

## 📋 Pre-Deployment Checklist

Before starting, make sure you have:
- ✅ Digital Ocean droplet running (68.183.88.5)
- ✅ SSH access to the server
- ✅ Your code pushed to GitHub: `https://github.com/Tharun2302/HYoda.git`
- ✅ Basic terminal/command line knowledge

---

## 🎯 Deployment Steps

### **STEP 1: Connect to Your Server**

Open your terminal (PowerShell on Windows, Terminal on Mac/Linux) and connect:

```bash
ssh root@68.183.88.5
```

**If this is your first time connecting:**
- You'll see a message about "authenticity of host"
- Type `yes` and press Enter
- Enter your password when prompted

**Expected output:**
```
Welcome to Ubuntu 22.04...
root@docker-ubuntu-s-4vcpu-8gb-amd-blr1-01:~#
```

---

### **STEP 2: Update System Packages**

Always good to start with updated packages:

```bash
apt update && apt upgrade -y
```

**What this does:** Updates all system packages to latest versions
**Time:** 2-5 minutes
**Expected:** Lots of text scrolling, ends with "Done"

---

### **STEP 3: Install Docker (if not already installed)**

Check if Docker is installed:

```bash
docker --version
```

**If Docker is NOT installed** (you get "command not found"), install it:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
```

**Verify installation:**
```bash
docker --version
```

**Expected output:** `Docker version 24.x.x` or similar

---

### **STEP 4: Install Docker Compose**

Check if Docker Compose is installed:

```bash
docker-compose --version
```

**If NOT installed**, install it:

```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

**Expected output:** `Docker Compose version v2.x.x`

---

### **STEP 5: Install Ollama**

This is the AI model server that will run your MedGemma model:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**What this does:** Downloads and installs Ollama service
**Time:** 1-2 minutes
**Expected:** Installation messages, ends with "Ollama installed successfully"

**Verify Ollama is installed:**
```bash
ollama --version
```

**Expected output:** `ollama version is x.x.x`

**Check if Ollama service is running:**
```bash
systemctl status ollama
```

**Expected:** Should show "active (running)" in green

**If Ollama is not running, start it:**
```bash
systemctl start ollama
systemctl enable ollama  # Make it start on boot
```

---

### **STEP 6: Download MedGemma Model**

This is the medical AI model (about 2.5GB download):

```bash
ollama pull alibayram/medgemma:4b
```

**What this does:** Downloads the MedGemma 4B model from Ollama's library
**Time:** 5-15 minutes (depends on internet speed)
**Expected:** Progress bar showing download, ends with "success"

**Verify model is downloaded:**
```bash
ollama list
```

**Expected output:**
```
NAME                      SIZE
alibayram/medgemma:4b     2.5 GB
```

**Test the model works:**
```bash
ollama run alibayram/medgemma:4b "What is hypertension?"
```

**Expected:** Model responds with medical information about hypertension
**To exit:** Press `Ctrl+D` or type `/bye`

---

### **STEP 7: Download Embedding Model (for RAG)**

This is needed for the question-answering system:

```bash
ollama pull nomic-embed-text
```

**Time:** 1-2 minutes
**Expected:** Download progress, ends with "success"

**Verify:**
```bash
ollama list
```

Should now show both models.

---

### **STEP 8: Clone Your Code from GitHub**

Navigate to `/opt` directory and clone your repository:

```bash
cd /opt
rm -rf hyoda  # Remove any old version
git clone https://github.com/Tharun2302/HYoda.git hyoda
cd hyoda
```

**What this does:** Downloads your code from GitHub
**Time:** 1-2 minutes
**Expected:** "Cloning into 'hyoda'..." then "done"

**Verify files are there:**
```bash
ls -la
```

**Expected:** Should see files like `app.py`, `docker-compose.yml`, `Dockerfile`, etc.

---

### **STEP 9: Create Environment Configuration File**

Create the `.env` file with all your settings:

```bash
cat > .env << 'EOF'
# Ollama Configuration (NO API KEY NEEDED - just the URL)
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=alibayram/medgemma:4b

# Langfuse Configuration (for analytics)
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

# CORS Configuration (YOUR SERVER IP)
ALLOWED_ORIGINS=http://68.183.88.5,http://68.183.88.5:8002,http://localhost:8002

# HealthBench Configuration (using Ollama)
HEALTHBENCH_GRADER_MODEL=alibayram/medgemma:4b
HELM_JUDGE_MODEL=alibayram/medgemma:4b

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
EOF
```

**What this does:** Creates configuration file with all settings
**Verify it was created:**
```bash
cat .env
```

**Expected:** Should show all the configuration values

---

### **STEP 10: Make Deployment Script Executable**

```bash
chmod +x deploy.sh
```

**What this does:** Makes the deployment script runnable
**Verify:**
```bash
ls -la deploy.sh
```

**Expected:** Should show `-rwxr-xr-x` (the `x` means executable)

---

### **STEP 11: Deploy the Application**

Now run the deployment script:

```bash
./deploy.sh
```

**What this does:**
1. Checks prerequisites
2. Builds Docker images (5-10 minutes first time)
3. Starts all containers (Flask app, MongoDB, Nginx)
4. Connects everything together

**Time:** 5-15 minutes (first time, faster after)
**Expected output:**
```
✓ Environment file found
✓ Prerequisites checked
Building Docker images...
✓ Docker images built
Starting services...
✓ All services started
Deployment completed successfully!
```

**If you see errors:**
- Read the error message carefully
- Common issues: Port already in use, missing files, Docker not running

---

### **STEP 12: Verify Everything is Running**

Check if all containers are up:

```bash
docker-compose ps
```

**Expected output:**
```
NAME              STATUS          PORTS
hyoda-chatbot     Up 2 minutes    0.0.0.0:8002->8002/tcp
hyoda-mongodb     Up 2 minutes    0.0.0.0:27017->27017/tcp
hyoda-nginx       Up 2 minutes    0.0.0.0:80->80/tcp
```

All should show "Up" status.

---

### **STEP 13: Check Application Logs**

See if the application started correctly:

```bash
docker-compose logs --tail=50 hyoda-app
```

**Look for these SUCCESS messages:**
- ✅ `Ollama client initialized: alibayram/medgemma:4b`
- ✅ `Ollama connected`
- ✅ `RAG System loaded`
- ✅ `MongoDB connected`
- ✅ `Running on http://0.0.0.0:8002`

**If you see errors:**
- Note the error message
- Common fixes:
  - Ollama not running: `systemctl restart ollama`
  - Port conflict: Check what's using port 8002
  - Missing files: Check if `docx/Question BOOK.docx` exists

---

### **STEP 14: Test Health Endpoint**

Test if the application is responding:

```bash
curl http://localhost:8002/health
```

**Expected output:**
```json
{"status":"healthy"}
```

**If you get connection refused:**
- Container might not be running: `docker-compose ps`
- Check logs: `docker-compose logs hyoda-app`

---

### **STEP 15: Test Ollama Connection from Container**

Verify Docker container can reach Ollama:

```bash
docker-compose exec hyoda-app curl http://host.docker.internal:11434/api/tags
```

**Expected output:** JSON with list of models including `medgemma:4b`

**If this fails:**
- Ollama might not be running: `systemctl status ollama`
- Check firewall: `ufw status`

---

### **STEP 16: Test in Browser**

Open your web browser and visit:

**Main Chatbot:**
```
http://68.183.88.5/index.html
```

**Dashboard:**
```
http://68.183.88.5/healthbench/dashboard
```

**Health Check:**
```
http://68.183.88.5/health
```

**Expected:**
- Chatbot page loads
- You can type a message
- Bot responds (may take 2-5 seconds)

---

### **STEP 17: Test a Conversation**

1. Go to: `http://68.183.88.5/index.html`
2. Type: "I have chest pain"
3. Wait 2-5 seconds
4. Bot should respond with medical questions

**If bot doesn't respond:**
- Check logs: `docker-compose logs -f hyoda-app`
- Check Ollama: `systemctl status ollama`
- Test Ollama directly: `ollama run alibayram/medgemma:4b "test"`

---

## 🔧 Troubleshooting Common Issues

### **Issue 1: "Cannot connect to Ollama"**

**Symptoms:** Error in logs about Ollama connection

**Fix:**
```bash
# Check if Ollama is running
systemctl status ollama

# If not running, start it
systemctl start ollama
systemctl enable ollama

# Verify it's accessible
curl http://localhost:11434/api/tags
```

---

### **Issue 2: "Port 8002 already in use"**

**Symptoms:** Container fails to start

**Fix:**
```bash
# Find what's using the port
lsof -i :8002
# or
netstat -tlnp | grep 8002

# Stop the conflicting service or change port in docker-compose.yml
```

---

### **Issue 3: "Model not found"**

**Symptoms:** Ollama can't find medgemma model

**Fix:**
```bash
# Check if model exists
ollama list

# If not there, pull it again
ollama pull alibayram/medgemma:4b
```

---

### **Issue 4: "Out of memory"**

**Symptoms:** Container crashes, OOMKilled

**Fix:**
- Your server has 8GB RAM, which should be enough
- Check memory: `free -h`
- If low, restart: `docker-compose restart`

---

### **Issue 5: "Cannot access from browser"**

**Symptoms:** Browser can't connect to server

**Fix:**
```bash
# Check if firewall is blocking
ufw status

# Allow HTTP traffic
ufw allow 80/tcp
ufw allow 8002/tcp

# Check if containers are running
docker-compose ps
```

---

## 📊 Monitoring Commands

**View all logs:**
```bash
docker-compose logs -f
```

**View only app logs:**
```bash
docker-compose logs -f hyoda-app
```

**Check resource usage:**
```bash
docker stats
```

**Check Ollama status:**
```bash
systemctl status ollama
ollama list
```

**Restart everything:**
```bash
docker-compose restart
```

**Stop everything:**
```bash
docker-compose down
```

**Start everything:**
```bash
docker-compose up -d
```

---

## ✅ Success Checklist

After deployment, verify:

- [ ] Ollama is running: `systemctl status ollama`
- [ ] Models are downloaded: `ollama list` shows medgemma and nomic-embed-text
- [ ] Containers are up: `docker-compose ps` shows all "Up"
- [ ] Health check works: `curl http://localhost:8002/health` returns `{"status":"healthy"}`
- [ ] Ollama accessible from container: `docker-compose exec hyoda-app curl http://host.docker.internal:11434/api/tags`
- [ ] Browser access works: Can open `http://68.183.88.5/index.html`
- [ ] Chatbot responds: Can have a conversation

---

## 🎉 You're Done!

If all checks pass, your deployment is complete!

**Your application is now running at:**
- **Chatbot:** http://68.183.88.5/index.html
- **Dashboard:** http://68.183.88.5/healthbench/dashboard
- **API:** http://68.183.88.5:8002

**Next Steps:**
- Test various medical scenarios
- Monitor performance
- Set up backups (optional)
- Configure SSL/HTTPS (optional, for production)

---

## 📞 Need Help?

If you encounter issues:
1. Check the logs: `docker-compose logs -f hyoda-app`
2. Verify Ollama: `systemctl status ollama`
3. Check containers: `docker-compose ps`
4. Review this guide step-by-step

**Common fixes:**
- Restart Ollama: `systemctl restart ollama`
- Restart containers: `docker-compose restart`
- Rebuild: `docker-compose up -d --build`

---

**Good luck with your deployment! 🚀**

