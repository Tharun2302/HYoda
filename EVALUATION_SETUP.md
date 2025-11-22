# HealthBench Evaluation Setup Guide

## Overview

HYoda bot now includes real-time evaluation of bot questions using HealthBench rubrics. Each question the bot asks is automatically evaluated against medical best practices, and scores are logged to your Langfuse dashboard.

## Features

✅ **Real-time evaluation** - Bot questions evaluated as they're generated  
✅ **Auto-detect medical domain** - Rubrics automatically selected based on conversation context  
✅ **Langfuse integration** - All scores visible in your Langfuse dashboard  
✅ **Detailed rubrics** - Each rubric criterion evaluated separately with explanations  
✅ **Zero disruption** - Evaluation failures don't break the chat experience  

## Setup Instructions

### 1. Prerequisites

Make sure you have:
- OpenAI API key (for both bot and evaluation)
- Langfuse account and keys (to view evaluation scores)
- Python dependencies installed

### 2. Install Additional Dependencies

The evaluation system requires the `blobfile` package:

```bash
pip install blobfile
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
# Required
OPENAI_API_KEY=sk-your-actual-api-key

# Required for evaluation dashboard
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional - Evaluation settings
HEALTHBENCH_EVAL_ENABLED=true
HEALTHBENCH_GRADER_MODEL=gpt-4o-mini
```

### 4. Start the Bot

```bash
cd HYoda
python app.py
```

You should see these startup messages:

```
✅ HealthBench evaluation modules loaded
✅ RAG System loaded: XXX questions available
✅ Evaluation system initialized (grader: gpt-4o-mini)
```

### 5. Test the Evaluation

Start a conversation with the bot. For each bot response, you'll see:

```
[EVALUATION] Starting HealthBench evaluation...
[EVALUATION] ✅ Score: 0.85 (8/10 passed)
✅ Logged 12 scores to Langfuse for trace abc123
```

## Viewing Results in Langfuse Dashboard

### Access Your Dashboard

1. Go to your Langfuse URL (e.g., `https://cloud.langfuse.com`)
2. Log in with your credentials
3. Select your project

### Navigate to Scores

**Option 1: View by Trace**
1. Go to **Traces** tab
2. Click on any conversation trace
3. Scroll down to **Scores** section
4. You'll see multiple scores:
   - `healthbench_overall_score` - Overall evaluation score (0-1)
   - `healthbench_pass_rate` - Percentage of rubrics passed
   - `healthbench_rubric_*` - Individual rubric scores

**Option 2: Aggregate View**
1. Go to **Scores** tab (if available in your Langfuse plan)
2. Filter by score name prefix: `healthbench_`
3. View statistics and trends

### Understanding the Scores

Each score includes:

- **Name**: e.g., `healthbench_rubric_cardiac_onset_0`
- **Value**: `1.0` (passed) or `0.0` (failed)
- **Comment**: Explanation of why the rubric passed or failed
- **Metadata**: 
  - Rubric criterion text
  - Points value
  - Tags (medical domain, category)
  - Medical context

## Configuration Options

### Evaluation Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTHBENCH_EVAL_ENABLED` | `true` | Enable/disable evaluation |
| `HEALTHBENCH_GRADER_MODEL` | `gpt-4o-mini` | Model for grading (gpt-4o-mini or gpt-4) |

### Performance Considerations

- **Grader Model Choice**:
  - `gpt-4o-mini`: Faster (~1-2s per turn), cheaper, good accuracy
  - `gpt-4`: Slower (~2-3s per turn), more expensive, higher accuracy

- **Latency Impact**: 
  - Evaluation adds 1.5-2.5 seconds per turn
  - Runs after bot response, so doesn't delay response streaming
  - Users see responses immediately, evaluation happens in background

### Disabling Evaluation

To disable evaluation temporarily:

```env
HEALTHBENCH_EVAL_ENABLED=false
```

Or remove Langfuse keys from `.env`.

## Troubleshooting

### Evaluation Not Starting

**Symptom**: No evaluation messages in console

**Solutions**:
1. Check `HEALTHBENCH_EVAL_ENABLED=true` in `.env`
2. Verify `blobfile` is installed: `pip install blobfile`
3. Check console for error messages during startup

### Scores Not Appearing in Langfuse

**Symptom**: Evaluation runs but scores missing in dashboard

**Solutions**:
1. Verify Langfuse keys are correct in `.env`
2. Check Langfuse connection: Look for trace IDs in console
3. Wait a few seconds and refresh Langfuse dashboard
4. Check Langfuse API status

### Evaluation Errors Don't Break Chat

By design, evaluation errors are caught and logged but don't interrupt the conversation. Check console output for error details.

## Medical Domain Detection

The evaluation system automatically detects the medical domain from:

1. **RAG tree_path**: e.g., "Cardiac System > Chest Pain > Onset/Duration"
2. **Conversation context**: Keywords in recent messages
3. **Fallback**: General medical rubrics if domain unclear

Supported domains:
- Cardiac System
- Respiratory System
- GI System
- Neurologic System
- Musculoskeletal System
- GU System
- Dermatologic System
- General/Endocrine/Infectious Disease System
- ENT/Eye System

## Example Evaluation Output

```
[CHATBOT RESPONSE]
================================================================================
[TREE BRANCH] Cardiac System > Chest Pain > Onset/Duration
[TAGS] cardiac, chest_pain
[USER] I've been having chest pain
[BOT] I understand you're experiencing chest pain. Can you tell me when it started?
================================================================================

[EVALUATION] Starting HealthBench evaluation...
✅ Loaded 850 HealthBench examples with rubrics
[RAG] Semantic search found 5 relevant questions
✅ Evaluation completed in 2.15s - Score: 0.90
[EVALUATION] ✅ Score: 0.90 (9/10 passed)
✅ Logged 12 scores to Langfuse for trace cm3xb8z...
```

## Cost Estimates

Evaluation costs depend on:
- Number of conversation turns
- Grader model choice
- Number of rubrics evaluated per turn

**Approximate costs per turn:**
- Using `gpt-4o-mini`: $0.001-0.003 per turn (~10 rubrics)
- Using `gpt-4`: $0.01-0.03 per turn (~10 rubrics)

A 10-turn conversation:
- `gpt-4o-mini`: ~$0.01-0.03 total
- `gpt-4`: ~$0.10-0.30 total

## Support

For issues or questions:
1. Check console output for detailed error messages
2. Review Langfuse dashboard for trace details
3. Verify all environment variables are set correctly
4. Ensure `simple-evals` folder is in the parent directory of `HYoda`

