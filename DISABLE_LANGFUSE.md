# How to Disable Langfuse Tracing

## Option 1: Add Disable Flag to .env (Recommended)

Add this line to your `.env` file:

```bash
LANGFUSE_ENABLED=false
```

Then restart the app:
```bash
python app.py
```

You'll see:
```
[!] Langfuse explicitly disabled (LANGFUSE_ENABLED=false)
```

---

## Option 2: Remove Langfuse Keys (Alternative)

Comment out or remove these lines from `.env`:

```bash
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## What Happens When Disabled

### Still Works:
- ✅ Chatbot responses
- ✅ HealthBench evaluation (Overall, Safety, Tag scores)
- ✅ Red flag detection
- ✅ Results saved to healthbench_results.json
- ✅ Console output with all scores

### Won't Work:
- ❌ Langfuse dashboard logging
- ❌ Trace visualization in Langfuse UI
- ❌ Feedback submission to Langfuse

---

## Console Output Differences

### With Langfuse:
```
[OK] Langfuse initialized
[EVALUATION] [OK] Overall Score: 0.85
[LANGFUSE SCORER] ✅ Logged 15 scores to Langfuse
```

### Without Langfuse:
```
[!] Langfuse explicitly disabled
[EVALUATION] [OK] Overall Score: 0.85
[LANGFUSE SCORER] Langfuse client not provided, scoring disabled
```

**Everything still works - just no Langfuse dashboard logging!**

---

## To Re-enable Later

### Option 1:
Change in `.env`:
```bash
LANGFUSE_ENABLED=true
```

### Option 2:
Add back the Langfuse keys to `.env`

---

## Summary

**To disable Langfuse RIGHT NOW:**

1. Open `.env` file
2. Add this line:
   ```bash
   LANGFUSE_ENABLED=false
   ```
3. Restart: `python app.py`

**Done! ✅** 

All evaluation features still work, but nothing logs to Langfuse dashboard.

