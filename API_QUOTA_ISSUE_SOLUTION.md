# ⚠️ OpenAI API Quota Exceeded - Solution Guide

## 🚨 **The Issue**

```
Error code: 429 - You exceeded your current quota
```

**This is NOT a code bug!** This is an **OpenAI billing/quota issue**.

---

## 🔍 **What's Happening**

Your OpenAI API key has **run out of credits/quota**. When you try to:
1. Generate bot responses → **FAILS** (quota exceeded)
2. Run HealthBench evaluation → **FAILS** (quota exceeded)
3. Run HELM evaluation → **FAILS** (quota exceeded)

**Result:** Chatbot cannot respond, evaluations cannot run.

---

## ✅ **Solutions**

### **Solution 1: Add Credits to OpenAI Account** (Recommended)

1. Go to: https://platform.openai.com/account/billing
2. Log in with your OpenAI account
3. Click "Add payment method" or "Add credits"
4. Add funds ($5-10 minimum recommended)
5. Wait 5-10 minutes for quota to refresh
6. Restart your app: `python app.py`

---

### **Solution 2: Use Different API Key**

If you have another OpenAI key with available credits:

1. Edit your `.env` file
2. Replace the `OPENAI_API_KEY` value:
   ```bash
   OPENAI_API_KEY=sk-your-new-key-with-credits
   ```
3. Restart your app: `python app.py`

---

### **Solution 3: Temporarily Disable Evaluations** (Reduce API Usage)

While you fix billing, reduce API calls by disabling evaluations:

Edit `.env`:
```bash
# Disable both evaluations temporarily
HEALTHBENCH_EVAL_ENABLED=false
HELM_EVAL_ENABLED=false
```

**This reduces API usage by ~70%!**

- Bot responses: Still work (if quota allows)
- Evaluations: Disabled (saves API calls)

---

### **Solution 4: Check Your OpenAI Usage**

See how much you've used:

1. Go to: https://platform.openai.com/usage
2. Check current month usage
3. Check your billing limit
4. Verify if you need to increase limits

---

## 💰 **Understanding Your API Usage**

### **Per Chatbot Response:**
| Action | API Calls | Cost (approx) |
|--------|-----------|---------------|
| Bot response | 1 | $0.0001-0.0005 |
| HealthBench eval | 13 | $0.002-0.003 |
| HELM eval | 1 | $0.001-0.002 |
| **Total** | **15** | **$0.003-0.005** |

### **Your Usage (40 evaluations):**
- 40 responses × $0.003 = ~$0.12
- Plus bot generation costs
- **Total: ~$0.15-0.20**

**If you've exceeded quota with just 40 responses, your account likely has:**
- Free trial expired, or
- Very low credit limit ($5 or less)

---

## 🎯 **Current Error in Your System**

### **Where Errors Occur:**

1. **Frontend (index.html):**
   ```
   Error calling OpenAI API: Error code: 429
   ```
   **Cause:** Bot trying to generate response, quota exceeded

2. **Backend Evaluations:**
   ```
   [RAG] Semantic search failed: Error code: 429
   [EVALUATOR] Rubric failed: Error code: 429
   [HELM] Request failed: Error code: 429
   ```
   **Cause:** Evaluations trying to run, quota exceeded

**Everything fails because the API key has no credits left.**

---

## 🔧 **Temporary Workaround**

### **Disable Evaluations to Conserve API Calls:**

Edit `.env`:
```bash
# Keep bot working (if quota allows for basic responses)
HEALTHBENCH_EVAL_ENABLED=false
HELM_EVAL_ENABLED=false

# This removes 14 of 15 API calls per response
# Only 1 call for bot response remains
```

Restart app:
```bash
python app.py
```

**Now:**
- Bot responses: Work (if quota allows 1 call)
- Evaluations: Disabled (save API calls)

---

## 📊 **API Call Breakdown**

### **With Evaluations Enabled:**
```
User message → 
  Bot response (1 call) +
  HealthBench (13 calls) +
  HELM (1 call) +
  RAG embeddings (1 call) =
  16 TOTAL API CALLS per response
```

### **With Evaluations Disabled:**
```
User message →
  Bot response (1 call) +
  RAG embeddings (1 call) =
  2 TOTAL API CALLS per response
```

**Savings: 87% reduction in API usage!**

---

## ✅ **Recommended Actions**

### **Immediate (Right Now):**
```bash
# 1. Disable evaluations
echo "HEALTHBENCH_EVAL_ENABLED=false" >> .env
echo "HELM_EVAL_ENABLED=false" >> .env

# 2. Restart app
python app.py

# 3. Test if bot responds now (with reduced API usage)
```

### **Short-Term (Today):**
1. Add credits to OpenAI account
2. Wait for quota refresh (5-10 minutes)
3. Re-enable evaluations in `.env`
4. Restart app

### **Long-Term:**
1. Monitor usage: https://platform.openai.com/usage
2. Set appropriate billing limits
3. Consider usage-based budgeting

---

## 🎯 **Summary**

**Problem:** OpenAI API quota exceeded (Error 429)

**NOT a code bug!** Your code is perfect. The API key just needs credits.

**Solutions:**
1. ✅ Add credits to OpenAI account (permanent fix)
2. ✅ Use different API key with credits
3. ✅ Temporarily disable evaluations (reduce usage)
4. ✅ Check and increase billing limits

**Immediate workaround:**
```bash
# Add to .env:
HEALTHBENCH_EVAL_ENABLED=false
HELM_EVAL_ENABLED=false
```

This will reduce API usage by 87% while you add credits!

---

*Issue: API Quota/Billing (not code bug)*
*Fix: Add credits to OpenAI account*
*Workaround: Disable evaluations temporarily*

