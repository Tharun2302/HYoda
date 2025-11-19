# System Prompt Review - HealthYODA

**Date:** December 2024  
**Status:** ⚠️ **Several Issues Found - Needs Code Updates**

---

## Executive Summary

Your new system prompt is well-structured and comprehensive, but there are **critical gaps** between what the prompt expects and what the code currently implements. The prompt uses template variables that aren't being populated, and several features mentioned in the prompt aren't implemented in the code.

---

## ✅ What WILL Work

### 1. Basic RAG Integration ✅
- **Status:** Working
- **Code:** Lines 382-410 in `app.py`
- **How it works:** RAG system retrieves relevant questions and adds them to context
- **Note:** Only adds one question at a time, not the full checklist

### 2. Conversation History ✅
- **Status:** Working
- **Code:** Lines 373-380, 419 in `app.py`
- **How it works:** Maintains conversation history, sends last 20 messages to OpenAI
- **Note:** This supports the "adaptive questioning" requirement

### 3. Prohibitions (No Medical Advice) ✅
- **Status:** Will work (LLM will follow instructions)
- **Prompt:** Lines 249-267
- **How it works:** LLM will follow the strict prohibitions in the prompt
- **Note:** No code-level enforcement, relies on prompt engineering

### 4. Safety Behavior (Life-threatening symptoms) ✅
- **Status:** Will work (LLM will follow instructions)
- **Prompt:** Lines 269-275
- **How it works:** LLM instructed to close session for life-threatening symptoms
- **Note:** No code-level detection or enforcement

---

## ⚠️ What WON'T Work (Critical Issues)

### 1. Template Variables Not Populated ❌

**Issue:** The prompt uses `{{COMPLAINT_NAME}}` and `{{COMPLAINT_JSON_CHECKLIST}}` but these are never replaced.

**Evidence:**
- Prompt line 152: `Complaint: {{COMPLAINT_NAME}}`
- Prompt line 154: `RAG Question Set: {{COMPLAINT_JSON_CHECKLIST}}`
- Prompt line 290: `"complaint": "{{COMPLAINT_NAME}}"`
- Code line 413: `enhanced_system_prompt = SYSTEM_PROMPT` (no replacement)

**Impact:** The LLM will see literal `{{COMPLAINT_NAME}}` text, which is confusing and unprofessional.

**Fix Required:**
```python
# Need to extract complaint from conversation or request
complaint_name = extract_complaint_from_conversation(conversation_history)
complaint_checklist = get_complaint_checklist_json(complaint_name, rag_system)

# Replace template variables
enhanced_system_prompt = SYSTEM_PROMPT.replace('{{COMPLAINT_NAME}}', complaint_name or 'Not specified')
enhanced_system_prompt = enhanced_system_prompt.replace('{{COMPLAINT_JSON_CHECKLIST}}', complaint_checklist or '[]')
```

---

### 2. RAG Question Set Format Mismatch ❌

**Issue:** Prompt expects `{{COMPLAINT_JSON_CHECKLIST}}` (full JSON checklist), but code only provides one question at a time.

**Evidence:**
- Prompt line 154: Expects full checklist JSON
- Code lines 397-401: Only adds one question: `rag_context = f"\n\n[RELEVANT QUESTION FROM QUESTION BOOK]\n"`

**Impact:** LLM doesn't have the full context of available questions, can't track completion properly.

**Fix Required:**
```python
# Get all questions for the complaint/symptom, not just one
complaint_questions = rag_system.get_all_questions_for_complaint(complaint_name)
complaint_json = json.dumps(complaint_questions, indent=2)
```

---

### 3. Structured JSON Output Not Parsed ❌

**Issue:** Prompt requires structured JSON output at session end (lines 284-317), but code doesn't parse or handle it.

**Evidence:**
- Prompt lines 288-317: Requires `[STRUCTURED_JSON]` output
- Code line 484: Just stores response as text: `conversation_history.append({'role': 'assistant', 'content': full_response})`

**Impact:** The structured JSON will be generated but not extracted or stored separately for the physician.

**Fix Required:**
```python
# Parse structured JSON from response
import re
json_match = re.search(r'\[STRUCTURED_JSON\]\s*(\{.*?\})', full_response, re.DOTALL)
if json_match:
    structured_data = json.loads(json_match.group(1))
    # Store separately for physician access
    store_structured_history(session_id, structured_data)
```

---

### 4. Session Completion Detection Not Implemented ❌

**Issue:** Prompt says "Once all domains are fully covered" (line 278), but code doesn't track completion.

**Evidence:**
- Prompt line 278: Requires tracking completion
- Prompt line 247: "Track which domains are Completed / Pending"
- Code: No domain tracking or completion detection

**Impact:** LLM will try to track completion in its own memory, but it's unreliable. No way to know when interview is complete.

**Fix Required:**
```python
# Track domains covered
session_state = {
    'hpi_complete': False,
    'ros_complete': False,
    'past_history_complete': False,
    'red_flags_checked': False,
    'domains_covered': []
}

# Check completion
if all([session_state['hpi_complete'], session_state['ros_complete'], ...]):
    # Trigger summary generation
    pass
```

---

### 5. Red Flag Detection Not Implemented ❌

**Issue:** Prompt mentions red flags (line 233-234, 316) but no code-level detection or prioritization.

**Evidence:**
- Prompt line 234: "prioritize those questions immediately"
- Code: No red flag detection logic
- RAG system has red flag questions (line 442 in `rag_system.py`) but they're not prioritized

**Impact:** Red flags won't be prioritized automatically - relies entirely on LLM following instructions.

**Fix Required:**
```python
# Detect red flags in user input
red_flag_keywords = ['chest pain', 'trouble breathing', 'severe bleeding', ...]
if any(keyword in question.lower() for keyword in red_flag_keywords):
    # Prioritize red flag questions
    rag_question_info = rag_system.get_next_question(
        current_category='Red Flags',
        priority=True
    )
```

---

### 6. Question Length Limit Not Enforced ❌

**Issue:** Prompt says "Ask one question at a time (≤ 12 words)" (line 237), but no enforcement.

**Evidence:**
- Prompt line 237: ≤ 12 words requirement
- Code: No word count checking or enforcement
- `max_tokens=1000` allows much longer responses

**Impact:** LLM may generate longer questions, violating the requirement.

**Fix Required:**
```python
# Add to prompt or post-process response
# Option 1: Add to system prompt more explicitly
# Option 2: Post-process to truncate if > 12 words
# Option 3: Use function calling to enforce structure
```

---

### 7. Summary Note Extraction Not Implemented ❌

**Issue:** Prompt requires `[SUMMARY_NOTE]` output (line 285-286), but code doesn't extract it.

**Evidence:**
- Prompt lines 280-282: Requires summary
- Prompt line 285: Requires `[SUMMARY_NOTE]` marker
- Code: No parsing of summary section

**Impact:** Summary will be generated but not extracted for separate storage/display.

**Fix Required:**
```python
# Extract summary note
summary_match = re.search(r'\[SUMMARY_NOTE\]\s*(.*?)(?=\[STRUCTURED_JSON\]|$)', full_response, re.DOTALL)
if summary_match:
    summary_note = summary_match.group(1).strip()
    # Store separately
```

---

## 🔧 Medium Priority Issues

### 8. Complaint Name Extraction Not Implemented ⚠️

**Issue:** Need to extract complaint name from conversation to populate `{{COMPLAINT_NAME}}`.

**Current:** No complaint extraction logic.

**Fix Required:**
```python
def extract_complaint_from_conversation(conversation_history):
    """Extract chief complaint from conversation"""
    # Look for complaint in first few messages
    # Could use LLM to extract, or keyword matching
    # Or require it as input parameter
    pass
```

---

### 9. Domain Tracking Not Implemented ⚠️

**Issue:** Prompt requires tracking "Completed / Pending" domains (line 247), but no state management.

**Current:** No domain tracking.

**Fix Required:**
```python
# Track which HPI elements covered
hpi_elements_covered = {
    'onset': False,
    'location': False,
    'duration': False,
    # ... etc
}

# Update based on conversation
# Pass to LLM as context
```

---

### 10. Session Closing Logic Not Implemented ⚠️

**Issue:** Prompt says "Then close the session" (line 275) for life-threatening symptoms, but no code handles this.

**Current:** No session closing logic.

**Fix Required:**
```python
# Detect if LLM indicates session should close
if '[SESSION_CLOSE]' in full_response or 'close the session' in full_response.lower():
    # Mark session as closed
    # Don't accept further messages
    pass
```

---

## 📋 Recommendations

### Immediate Fixes (Critical)

1. **Populate Template Variables**
   - Extract complaint name from conversation or require as input
   - Generate full complaint checklist JSON from RAG system
   - Replace `{{COMPLAINT_NAME}}` and `{{COMPLAINT_JSON_CHECKLIST}}`

2. **Implement Structured Output Parsing**
   - Parse `[SUMMARY_NOTE]` section
   - Parse `[STRUCTURED_JSON]` section
   - Store structured data separately

3. **Add Red Flag Detection**
   - Detect red flag keywords in user input
   - Prioritize red flag questions from RAG
   - Alert/flag in system

### Short-Term Fixes (High Priority)

4. **Implement Domain Tracking**
   - Track HPI elements covered
   - Track ROS systems reviewed
   - Track past history components
   - Pass completion status to LLM

5. **Add Session Completion Detection**
   - Check if all domains covered
   - Trigger summary generation
   - Handle session closing

6. **Enforce Question Length**
   - Add explicit instruction to system prompt
   - Or post-process to ensure ≤ 12 words
   - Consider using function calling for structured questions

### Long-Term Enhancements

7. **Complaint Extraction**
   - Use LLM to extract complaint from first message
   - Or require complaint as input parameter
   - Store complaint name in session state

8. **Enhanced RAG Integration**
   - Provide full question checklist, not just one question
   - Group questions by domain
   - Track which questions have been asked

---

## Code Changes Needed

### 1. Add Complaint Extraction
```python
def extract_complaint_name(conversation_history):
    """Extract chief complaint from conversation"""
    if len(conversation_history) > 0:
        first_user_msg = conversation_history[0].get('content', '')
        # Simple extraction or use LLM
        # For now, return None or require as input
    return None
```

### 2. Get Full Checklist
```python
def get_complaint_checklist_json(complaint_name, rag_system):
    """Get full JSON checklist for complaint"""
    if not complaint_name or not rag_system:
        return "[]"
    
    # Get all questions for this complaint
    questions = rag_system.search_by_symptom(complaint_name)
    # Format as JSON
    checklist = [{
        'domain': q.get('category', ''),
        'question': q.get('question', ''),
        'system': q.get('system', ''),
        'tags': q.get('tags', [])
    } for q in questions]
    
    return json.dumps(checklist, indent=2)
```

### 3. Parse Structured Output
```python
def parse_structured_output(full_response):
    """Extract summary note and structured JSON from response"""
    summary_note = None
    structured_json = None
    
    # Extract summary
    summary_match = re.search(r'\[SUMMARY_NOTE\]\s*(.*?)(?=\[STRUCTURED_JSON\]|$)', full_response, re.DOTALL)
    if summary_match:
        summary_note = summary_match.group(1).strip()
    
    # Extract JSON
    json_match = re.search(r'\[STRUCTURED_JSON\]\s*(\{.*?\})', full_response, re.DOTALL)
    if json_match:
        try:
            structured_json = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    return summary_note, structured_json
```

### 4. Update chat_stream Function
```python
# In chat_stream function, around line 412:
complaint_name = extract_complaint_name(conversation_history) or "Not specified"
complaint_checklist = get_complaint_checklist_json(complaint_name, rag_system)

# Replace template variables
enhanced_system_prompt = SYSTEM_PROMPT.replace('{{COMPLAINT_NAME}}', complaint_name)
enhanced_system_prompt = enhanced_system_prompt.replace('{{COMPLAINT_JSON_CHECKLIST}}', complaint_checklist)

# After getting full_response, parse structured output
summary_note, structured_json = parse_structured_output(full_response)
if structured_json:
    # Store structured data
    store_structured_history(session_id, structured_json)
```

---

## Testing Checklist

- [ ] Template variables are replaced (not showing `{{COMPLAINT_NAME}}` literally)
- [ ] Full complaint checklist is provided to LLM
- [ ] Structured JSON is extracted and stored
- [ ] Summary note is extracted
- [ ] Red flags are detected and prioritized
- [ ] Domain tracking works
- [ ] Session completion is detected
- [ ] Questions are ≤ 12 words (or enforced)
- [ ] Session closing works for life-threatening symptoms

---

## Conclusion

Your system prompt is excellent and comprehensive, but **the code needs significant updates** to support all the features it describes. The most critical issues are:

1. Template variables not populated
2. Structured output not parsed
3. Domain tracking not implemented
4. Red flag detection not implemented

**Priority:** Fix template variables first (easiest, biggest impact), then structured output parsing, then domain tracking.

Would you like me to implement these fixes?

