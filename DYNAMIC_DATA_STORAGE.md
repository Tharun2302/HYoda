# Dynamic Data Storage with Q&A Pairs

**Date:** November 20, 2024  
**Status:** ✅ **Implemented**

---

## Problem

### Issues with Predefined Keys:

1. **"No" responses not stored**: When patient says "no", data wasn't stored because predefined fields only store positive values
2. **Bot repeats questions**: Since "no" wasn't stored, bot thought data wasn't collected and asked again
3. **Limited to predefined structure**: Only stored data that matched predefined keys (onset, location, quality, etc.)
4. **Lost context**: No record of what questions were actually asked

**Example from logs:**
```
Bot: "Do you have fever?"
User: "no"
MongoDB: (nothing stored - "no" doesn't fit predefined keys)
Later...
Bot: "Do you have fever?" (asks again!)
```

---

## Solution

### 1. Store ALL Question-Answer Pairs

**New field in MongoDB: `qa_pairs`**

```json
{
  "session_id": "...",
  "qa_pairs": [
    {
      "question": "Do you have fever?",
      "answer": "no",
      "timestamp": "2024-11-20T14:30:00"
    },
    {
      "question": "When did the pain start?",
      "answer": "yesterday",
      "timestamp": "2024-11-20T14:30:15"
    },
    {
      "question": "Do you smoke?",
      "answer": "no",
      "timestamp": "2024-11-20T14:30:30"
    }
  ],
  "hpi": {...},
  "ros": {...}
}
```

**Benefits:**
- ✅ Stores "no" responses
- ✅ Bot knows question was already asked
- ✅ Complete conversation record
- ✅ No data lost

### 2. Dynamic Field Names (No Predefined Keys)

**Before (predefined):**
```json
{
  "onset": "yesterday",
  "location": "shoulder", 
  "quality": "sharp"
}
```

**After (dynamic):**
```json
{
  "symptom_onset": "yesterday",
  "pain_location": "shoulder",
  "pain_description": "sharp, stabbing",
  "pain_frequency": "constant",
  "fever_status": "no",
  "smoking_status": "no"
}
```

LLM creates field names based on what was asked, not limited to predefined structure.

### 3. Question Similarity Check

Before asking a question, check if similar question was already asked:

```python
def was_question_asked(session_id, new_question):
    # Check Q&A pairs for similar questions
    # Uses keyword matching (can be enhanced with embeddings)
    # Returns True if question already asked
```

**Example:**
- Already asked: "When did the pain start?"
- New question: "When did it begin?"
- Result: 3+ common keywords → Skip (already asked)

---

## How It Works

### Flow for Every Response:

1. **User responds** to bot question
2. **Store Q&A pair** in `qa_pairs` array (including "no")
   ```python
   store_qa_pair(session_id, bot_question, user_response)
   ```
3. **IF response > 3 chars** (not just "no"), extract structured data
   ```python
   extract_and_store_data_with_llm(...)
   ```
4. **LLM creates dynamic fields** based on question
5. **Store in appropriate section** (HPI/ROS/Past History)
6. **Bot sees collected data** in context
7. **Bot asks next question** (not duplicate)

### Example Session:

**Question 1:**
```
Bot: "Do you have fever?"
User: "no"
```

**Stored:**
```json
{
  "qa_pairs": [
    {"question": "Do you have fever?", "answer": "no", "timestamp": "..."}
  ],
  "ros": {
    "fever_status": "no"
  }
}
```

**Question 2:**
```
Bot: "Any fever?" (similar to previous)
```

**Result:**
- Check Q&A pairs → "Do you have fever?" already asked
- Skip question → Ask something else ✅

---

## Code Changes

### New Functions:

**1. `store_qa_pair(session_id, question, answer)`**
- Stores every question-answer pair
- Includes timestamp
- Works for ALL responses including "no"

```python
qa_pairs.append({
    'question': question,
    'answer': answer,
    'timestamp': datetime.now().isoformat()
})
```

**2. `was_question_asked(session_id, new_question)`**
- Checks if similar question already asked
- Uses keyword overlap (3+ words in common)
- Returns True/False

**3. Updated `extract_and_store_data_with_llm()`**
- ALWAYS stores Q&A pair first
- Then extracts structured data if meaningful
- Creates dynamic field names (no predefined keys)
- Categorizes by content (HPI/ROS/Past History)

**4. Updated `format_collected_data_for_llm()`**
- Shows last 15 Q&A pairs
- Shows structured data
- Clear warning: DON'T RE-ASK

---

## Benefits

### 1. No Duplicate Questions ✅

**Before:**
```
Bot: "Do you smoke?"
User: "no"
(not stored)
Bot: "Do you smoke?" (asks again)
```

**After:**
```
Bot: "Do you smoke?"
User: "no"
Stored: qa_pairs + smoking_status: "no"
Bot: (sees question was asked) → Asks different question ✅
```

### 2. "No" Responses Stored ✅

All responses stored, including:
- "no"
- "none"
- "never"
- "not really"

Bot knows these were asked and answered.

### 3. Flexible Structure ✅

Not limited to predefined keys. LLM creates appropriate field names:
- `symptom_onset`
- `pain_location`
- `fever_status`
- `smoking_status`
- `alcohol_consumption`
- etc.

### 4. Complete Record ✅

Every Q&A pair stored = complete conversation history for doctors.

---

## Context for LLM

**Before (only structured data):**
```
HPI Data Already Collected: onset, location, quality
```

**After (Q&A + structured):**
```
[INFORMATION ALREADY COLLECTED - DO NOT RE-ASK]
======================================================================
QUESTIONS ALREADY ASKED:
  Q: Do you have fever?
  A: no
  Q: When did the pain start?
  A: yesterday
  Q: Do you smoke?
  A: no

STRUCTURED HPI DATA:
  - symptom_onset: yesterday
  - pain_location: right shoulder
  - fever_status: no

PAST HISTORY:
  - smoking_status: no
======================================================================
⚠️  CRITICAL: DO NOT ask questions that were already asked above!
Focus ONLY on collecting NEW information.
```

LLM sees:
- Exact questions already asked
- User's actual responses
- Structured extracted data
- Clear instruction not to repeat

---

## MongoDB Structure

```json
{
  "_id": ObjectId("..."),
  "session_id": "cf.conversation.20241120.abc123",
  "complaint_name": "shoulder pain",
  
  "qa_pairs": [
    {"question": "What brings you in?", "answer": "shoulder pain", "timestamp": "..."},
    {"question": "When did it start?", "answer": "yesterday", "timestamp": "..."},
    {"question": "Do you have fever?", "answer": "no", "timestamp": "..."},
    {"question": "Do you smoke?", "answer": "no", "timestamp": "..."}
  ],
  
  "hpi": {
    "chief_complaint": "shoulder pain",
    "symptom_onset": "yesterday",
    "pain_location": "right shoulder",
    "pain_description": "aching",
    "fever_status": "no"
  },
  
  "ros": {
    "constitutional": "no fever, no weight loss"
  },
  
  "past_history": {
    "smoking_status": "no",
    "alcohol_status": "no",
    "pmh": null,
    "medications": []
  },
  
  "red_flags": [],
  "created_at": "2024-11-20T14:25:00",
  "updated_at": "2024-11-20T14:35:00"
}
```

---

## Testing

### Test Scenario:

1. Start conversation
2. Answer some questions with "no"
3. Check MongoDB `qa_pairs` array
4. Bot should NOT ask same questions again

**Check in MongoDB:**
```python
session = db['patient_sessions'].find_one({'session_id': 'your_session'})
print("Q&A Pairs:", len(session['qa_pairs']))
for qa in session['qa_pairs']:
    print(f"Q: {qa['question']}")
    print(f"A: {qa['answer']}\n")
```

**Expected:**
- All Q&A pairs stored (including "no" responses)
- No duplicate questions asked
- Structured data extracted where meaningful

---

## Logs

**Before:**
```
[User] no
(Nothing stored)

Bot asks same question later...
```

**After:**
```
[MongoDB] Stored Q&A: Q='Do you have fever?' A='no'
[LLM Extract] ros.fever_status: no
[MongoDB] Stored 1 dynamic fields

Later when similar question comes up:
[MongoDB] Similar question already asked: 'Do you have fever?'
(Bot asks different question)
```

---

## Future Enhancements

### 1. Semantic Similarity
- Use embeddings instead of keyword matching
- Better detection of similar questions
- "When did it start?" = "When did it begin?"

### 2. Answer Conflict Detection
- User says "no fever" initially
- Later says "I had fever yesterday"
- Flag inconsistency for doctor review

### 3. Intelligent Follow-ups
- User says "no" to fever
- Don't ask "how high was the fever?"

### 4. Data Validation
- Check if answer makes sense for question
- "When did it start?" → "purple" = flag for review

---

## Summary

✅ **Stores ALL responses** - Including "no", "none", "never"  
✅ **No duplicate questions** - Checks Q&A pairs before asking  
✅ **Dynamic fields** - No predefined structure limits  
✅ **Complete record** - Every Q&A pair stored  
✅ **Better context** - LLM sees what was already asked  
✅ **Flexible extraction** - Creates appropriate field names  

The bot now stores every question and answer, preventing duplicates and creating a complete medical record regardless of response type.

