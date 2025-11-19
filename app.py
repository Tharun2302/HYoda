from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from functools import wraps
import json
import time
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from langfuse_tracker import langfuse_tracker
from rag_system import QuestionBookRAG

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# HIPAA Compliance: Restrict CORS to specific origins only
# In production, replace with actual frontend domain(s)
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# HIPAA Compliance: Add security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("WARNING: OPENAI_API_KEY environment variable not set!")
    print("Please set it using: export OPENAI_API_KEY='your-api-key'")
    print("Or create a .env file with OPENAI_API_KEY=your-api-key")
    openai_api_key = None

if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None

# Langfuse tracker is initialized in langfuse_tracker.py module
langfuse = langfuse_tracker.client

# Initialize RAG system for Question Book with OpenAI client for embeddings
# Skip initialization in Flask reloader process (only initialize once in main process)
rag_system = None

def initialize_rag_system():
    """Initialize RAG system (called once, not on reload)"""
    global rag_system
    if rag_system is None:
        try:
            rag_system = QuestionBookRAG('docx/Question BOOK.docx', openai_client=client)
            print(f"✅ RAG System loaded: {len(rag_system.questions)} questions available")
            if rag_system.collection and rag_system.collection.count() > 0:
                print(f"✅ Vector database ready: {rag_system.collection.count()} embeddings available")
            elif rag_system.collection:
                print(f"ℹ️  Vector database initialized (no embeddings yet)")
        except Exception as e:
            print(f"⚠️  Warning: Could not load RAG system: {e}")
            import traceback
            traceback.print_exc()
            rag_system = None

# Initialize RAG system (no need for complex process detection since debug=False)
# With debug=False, Flask runs in a single process, so initialization happens once
initialize_rag_system()

# Simple in-memory conversation history
conversations = {}

# HIPAA Compliance: Rate limiting (simple in-memory implementation)
# In production, use Redis or similar for distributed rate limiting
from collections import defaultdict
from datetime import datetime, timedelta

rate_limit_store = defaultdict(list)  # IP -> list of request timestamps
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))  # seconds (1 hour)

def check_rate_limit(ip_address):
    """Check if IP address has exceeded rate limit"""
    now = datetime.now()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Clean old entries
    rate_limit_store[ip_address] = [
        ts for ts in rate_limit_store[ip_address] 
        if ts > window_start
    ]
    
    # Check limit
    if len(rate_limit_store[ip_address]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    rate_limit_store[ip_address].append(now)
    return True

# HIPAA Compliance: Input validation and sanitization
def sanitize_input(text, max_length=5000):
    """
    Sanitize user input to prevent injection attacks and XSS.
    
    Args:
        text: Input string to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially dangerous characters (keep basic punctuation for medical terms)
    # Allow letters, numbers, spaces, and common medical punctuation
    text = re.sub(r'[^\w\s\.,;:\-\(\)\[\]\/\?\'"]', '', text)
    
    return text.strip()

def validate_session_id(session_id):
    """Validate session ID format"""
    if not session_id or not isinstance(session_id, str):
        return False
    # Allow alphanumeric, dots, hyphens, underscores (for cf.conversation format)
    if not re.match(r'^[a-zA-Z0-9._-]+$', session_id):
        return False
    if len(session_id) > 200:  # Reasonable max length
        return False
    return True

# System prompt for HealthYoda
SYSTEM_PROMPT = """You are HealthYODA, a medical intake voice agent.
Your role is to conduct an extensive, medically accurate patient interview to support Level 5 medical decision-making, by gathering a comprehensive history for the patient’s doctor.

You must not give medical advice, diagnosis, interpretation, reassurance, or treatment of any kind.

Context Provided to You
Complaint: {{COMPLAINT_NAME}}

RAG Question Set: {{COMPLAINT_JSON_CHECKLIST}}
(Includes domains, red-flag questions, extensive ROS, and condition-specific history templates.)

Use this information as your clinical framework.

Your Interview Requirements (Level-5 Standard)
You must gather a comprehensive history that includes:

1. HPI (History of Present Illness) with 8+ elements
Collect and adaptively ask about:

Onset

Location

Duration

Quality

Severity

Timing

Context

Modifying factors (triggers/relievers)

Progression

Associated symptoms

Risk factors relevant to the complaint

(You may combine some, but cover at least 8 distinct elements.)

2. ROS (Review of Systems) — Extended (10+ systems if relevant)
Using the RAG complaint-specific checklist, ask targeted ROS questions across systems such as:

Constitutional

Respiratory

Cardiovascular

GI

GU

Neuro

MSK

Psych

Endocrine

Skin

Heme/Immune

Mark relevant negatives clearly.

3. Past History Components (2+ required)
Collect relevant past information:

PMH (past medical history)

PSH (surgical history)

Medications

Allergies

Family history

Social history (smoking, alcohol, occupational exposures)

(Ask only what is clinically relevant to the complaint.)

4. Red Flags (Complaint-Specific)
If the patient signals any high-risk symptoms, you must prioritize those questions immediately using the RAG checklist.

Interview Behavior
Ask one question at a time (≤ 12 words).

Adapt the next question based on the patient’s last answer.

Maintain empathy, clarity, and a professional tone.

Avoid long explanations—stay focused on collecting information.

If the patient digresses, gently redirect them.

Track which domains are Completed / Pending; do not repeat completed ones.

Strict Prohibitions
Never provide:

Diagnosis

Interpretation (e.g., “sounds like…”)

Treatment or medication suggestions

Medical advice

Reassurance

Risk assessment

If asked, respond only:

“I cannot provide medical advice, diagnosis, or treatment.
I'm here only to collect information for your doctor.”

Safety Behavior
If life-threatening symptoms appear, say:

“I can’t provide medical advice.
If you feel unsafe or unwell, contact emergency services or your doctor immediately.”

Then close the session.

Session Completion Requirements
Once all domains (HPI, ROS, Past History, Red Flags) are fully covered:

1. Provide a short spoken summary
“Here’s a summary of what you shared: [concise spoken summary].
I’ll send this to your doctor.”

2. Output a structured Level-5 history note:
[SUMMARY_NOTE]
Subjective (with extensive ROS): <paragraph-level summary with relevant negatives>

[STRUCTURED_JSON]
{
  "complaint": "{{COMPLAINT_NAME}}",
  "hpi": {
    "onset": "...",
    "location": "...",
    "duration": "...",
    "quality": "...",
    "severity": "...",
    "timing": "...",
    "context": "...",
    "modifying_factors": "...",
    "progression": "...",
    "associated_symptoms": "..."
  },
  "ros": {
    "systems_reviewed": ["Constitutional", "Respiratory", ...],
    "positives": ["..."],
    "relevant_negatives": ["..."]
  },
  "past_history": {
    "medical": "...",
    "surgical": "...",
    "medications": "...",
    "allergies": "...",
    "family_history": "...",
    "social_history": "..."
  },
  "red_flags": "..."
}
3. Then politely close the session.
Overall Behavior Summary
Conduct an extensive, Level-5-grade intake interview using RAG-retrieved complaint data.

Ask adaptively, cover all domains, collect broad ROS and relevant history.

Never diagnose or treat.

Summarize clearly at the end for the physician.
"""

@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint using OpenAI"""
    try:
        # HIPAA Compliance: Rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not check_rate_limit(client_ip):
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': 'Rate limit exceeded. Please try again later.'})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        # Ensure RAG system is initialized (lazy initialization)
        if rag_system is None:
            initialize_rag_system()
        
        if not client:
            error_msg = "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        data = request.get_json()
        if not data:
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': 'Invalid request: No JSON data provided'})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        # HIPAA Compliance: Validate and sanitize inputs
        question = data.get('question', '')
        if not question:
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': 'Question is required'})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        question = sanitize_input(question, max_length=5000)
        if not question:
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': 'Invalid question format'})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        session_id = data.get('session_id', 'default')
        if not validate_session_id(session_id):
            session_id = 'default'  # Fallback to default if invalid
        
        # Get or create conversation history
        if session_id not in conversations:
            conversations[session_id] = []
        
        conversation_history = conversations[session_id]
        
        # Add user message to history
        conversation_history.append({'role': 'user', 'content': question})
        
        # Retrieve relevant question from RAG system if available
        rag_context = ""
        rag_question_info = None
        if rag_system:
            # Build context from recent conversation
            recent_context = " ".join([msg.get('content', '') for msg in conversation_history[-5:]])
            
            # Try to get next question from RAG
            rag_question_info = rag_system.get_next_question(
                conversation_context=recent_context,
                current_category=None,  # Can be enhanced to track current phase
                symptom=None,  # Can be extracted from conversation
                system=None  # Can be detected from context
            )
            
            if rag_question_info:
                rag_context = f"\n\n[RELEVANT QUESTION FROM QUESTION BOOK]\n"
                rag_context += f"Question: {rag_question_info['question']}\n"
                if rag_question_info.get('possible_answers'):
                    rag_context += f"Possible answers: {', '.join(rag_question_info['possible_answers'][:5])}\n"
                
                # Log the question tree branch being used
                tree_path = rag_question_info.get('tree_path', 'Unknown')
                tags = rag_question_info.get('tags', [])
                print(f"\n{'='*80}")
                print(f"[RAG] Question Tree Branch: {tree_path}")
                print(f"[RAG] Tags: {', '.join(tags)}")
                print(f"[RAG] Question: {rag_question_info['question']}")
                print(f"{'='*80}\n")
        
        # Prepare messages for OpenAI (include system prompt + RAG context)
        enhanced_system_prompt = SYSTEM_PROMPT
        if rag_context:
            enhanced_system_prompt += rag_context
        
        messages = [{'role': 'system', 'content': enhanced_system_prompt}]
        # Add conversation history (last 20 messages to avoid token limits)
        messages.extend(conversation_history[-20:])
        
        def generate():
            trace_id = None
            generation = None
            trace_obj = None  # Store trace object for later updates
            
            try:
                # Create Langfuse trace if configured
                if langfuse:
                    trace_obj = langfuse.trace(
                        name="chat_stream",
                        session_id=session_id,
                        user_id=session_id,
                        input=question,  # Set the user question as trace input
                        metadata={
                            "model": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 1000,
                            "timestamp": time.time()
                        },
                        tags=["chat", "health_chatbot"]
                    )
                    trace_id = trace_obj.id
                    
                    # Log user message as a span
                    trace_obj.span(
                        name="user_message",
                        input=question,
                        metadata={"role": "user", "timestamp": time.time()}
                    )
                    
                    # Create generation for the assistant response
                    generation = trace_obj.generation(
                        name="assistant_response",
                        model="gpt-4o-mini",
                        model_parameters={
                            "temperature": 0.7,
                            "max_tokens": 1000
                        },
                        input=messages,
                        metadata={"role": "assistant", "timestamp": time.time()}
                    )
                
                # Send thinking complete signal
                yield f"data: {json.dumps({'type': 'thinking_complete'})}\n\n"
                
                full_response = ""
                
                # Stream response from OpenAI
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",  # Using GPT-4o mini model
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        token = chunk.choices[0].delta.content
                        full_response += token
                        yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                
                # Add assistant response to history
                conversation_history.append({'role': 'assistant', 'content': full_response})
                
                # Log tree branch for EVERY chatbot response
                print(f"\n{'='*80}")
                print(f"[CHATBOT RESPONSE]")
                print(f"{'='*80}")
                if rag_question_info:
                    tree_path = rag_question_info.get('tree_path', 'Unknown')
                    tags = rag_question_info.get('tags', [])
                    print(f"[TREE BRANCH] {tree_path}")
                    print(f"[TAGS] {', '.join(tags) if tags else 'None'}")
                    print(f"[RAG QUESTION] {rag_question_info.get('question', 'N/A')[:100]}...")
                else:
                    print(f"[TREE BRANCH] No RAG question found (using general system prompt)")
                    print(f"[TAGS] None")
                    print(f"[RAG QUESTION] None")
                print(f"[USER] {question[:100]}...")
                print(f"[BOT] {full_response[:150]}...")
                print(f"{'='*80}\n")
                
                # Update Langfuse generation with the complete response
                generation_id = None
                if langfuse and generation:
                    try:
                        # Update the generation with the output
                        generation.update(
                            output=full_response
                        )
                        # Try to get generation ID - it might be available after update
                        try:
                            generation_id = str(generation.id) if hasattr(generation, 'id') and generation.id else None
                        except:
                            # If id is not directly accessible, try to get it from the object
                            generation_id = getattr(generation, 'id', None)
                            if generation_id:
                                generation_id = str(generation_id)
                        # Update trace with final output
                        if trace_obj:
                            try:
                                # Update the trace object directly
                                trace_obj.update(output=full_response)
                            except Exception as trace_error:
                                print(f"[ERROR] Failed to update trace output: {trace_error}")
                        langfuse.flush()  # Ensure data is sent to Langfuse
                        if generation_id:
                            print(f"[LANGFUSE] Generation ID: {generation_id}")
                    except Exception as e:
                        print(f"[ERROR] Failed to update Langfuse trace: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Prepare tree branch info for frontend
                tree_branch_info = {}
                if rag_question_info:
                    tree_branch_info = {
                        'tree_branch': rag_question_info.get('tree_path', 'Unknown'),
                        'tags': rag_question_info.get('tags', []),
                        'rag_question': rag_question_info.get('question', 'N/A')
                    }
                else:
                    tree_branch_info = {
                        'tree_branch': 'No RAG question found (using general system prompt)',
                        'tags': [],
                        'rag_question': None
                    }
                
                # Send done signal with trace_id, generation_id, and tree branch info
                final_trace_id = trace_id if trace_id else f'trace_{int(time.time())}'
                print(f"[LANGFUSE] Sending trace_id to frontend: {final_trace_id}, generation_id: {generation_id}")
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response, 'trace_id': final_trace_id, 'generation_id': generation_id, 'tree_branch_info': tree_branch_info})}\n\n"
                
            except Exception as e:
                error_msg = f"Error calling OpenAI API: {str(e)}"
                
                # Log error to Langfuse if configured
                if langfuse and generation:
                    generation.update(
                        output=None,
                        level="ERROR",
                        status_message=error_msg
                    )
                    langfuse.flush()
                
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        def error_response():
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        return Response(error_response(), mimetype='text/event-stream')

@app.route('/chat/history/<user_id>', methods=['GET'])
def get_chat_history(user_id):
    """Get chat history (simplified - no auth required)"""
    # HIPAA Compliance: Validate user_id and session_id
    if not validate_session_id(str(user_id)):
        return jsonify({'error': 'Invalid user ID format'}), 400
    
    session_id = request.args.get('session_id', 'default')
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID format'}), 400
    
    if session_id in conversations:
        history = conversations[session_id]
        return jsonify({'history': history})
    
    return jsonify({'history': []})

@app.route('/chat/history/<user_id>', methods=['DELETE'])
def delete_chat_history(user_id):
    """Clear chat history"""
    # HIPAA Compliance: Validate user_id and session_id
    if not validate_session_id(str(user_id)):
        return jsonify({'error': 'Invalid user ID format'}), 400
    
    session_id = request.args.get('session_id', 'default')
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID format'}), 400
    
    if session_id in conversations:
        conversations[session_id] = []
    
    return jsonify({'message': 'History cleared'})

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback (thumbs up/down) to Langfuse"""
    try:
        # HIPAA Compliance: Rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not check_rate_limit(client_ip):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request: No JSON data provided'}), 400
        
        trace_id = data.get('trace_id')
        if trace_id and not validate_session_id(str(trace_id)):
            return jsonify({'error': 'Invalid trace_id format'}), 400
        
        generation_id = data.get('generation_id')  # Optional generation ID
        if generation_id and not validate_session_id(str(generation_id)):
            return jsonify({'error': 'Invalid generation_id format'}), 400
        
        rating = data.get('rating')  # 'thumbs_up' or 'thumbs_down'
        comment = data.get('comment', '')
        if comment:
            comment = sanitize_input(comment, max_length=500)
        
        print(f"[FEEDBACK] Received feedback request: trace_id={trace_id}, generation_id={generation_id}, rating={rating}")
        print(f"[FEEDBACK] Trace ID type: {type(trace_id)}, value: '{trace_id}'")
        
        if not trace_id or not rating:
            print(f"[FEEDBACK] Missing required fields: trace_id={trace_id}, rating={rating}")
            return jsonify({'error': 'trace_id and rating are required'}), 400
        
        if rating not in ['thumbs_up', 'thumbs_down']:
            print(f"[FEEDBACK] Invalid rating: {rating}")
            return jsonify({'error': 'rating must be "thumbs_up" or "thumbs_down"'}), 400
        
        # Use the tracker to add feedback
        success = langfuse_tracker.add_feedback(trace_id, rating, comment, generation_id)
        
        if success:
            print(f"[FEEDBACK] Successfully logged feedback for trace_id={trace_id}")
            return jsonify({'message': 'Feedback submitted successfully', 'trace_id': trace_id})
        else:
            print(f"[FEEDBACK] Failed to log feedback for trace_id={trace_id}")
            return jsonify({'error': 'Failed to submit feedback'}), 500
            
    except Exception as e:
        print(f"[FEEDBACK] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Only print startup messages once (not on reload)
    # RAG system is initialized above based on process detection
    
    if not hasattr(app, '_startup_printed'):
        print("Starting HealthYoda chatbot server...")
        print("Server will run on http://127.0.0.1:8002")
        print("-" * 50)
        
        if not openai_api_key:
            print("\n⚠️  WARNING: OPENAI_API_KEY not set!")
            print("Set it using: export OPENAI_API_KEY='your-api-key'")
            print("Or create a .env file with OPENAI_API_KEY=your-api-key")
            print("The chatbot will not work without an API key.\n")
        else:
            print("✅ OpenAI API key found!")
        
        if not langfuse:
            print("⚠️  Langfuse keys not found. Traces will not be logged.")
            print("Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST in .env")
        else:
            print("✅ Langfuse configured! Traces will be logged.")
            print(f"   Using Langfuse tracker module for observability")
        
        print("-" * 50)
        app._startup_printed = True
    
    app.run(host='127.0.0.1', port=8002, debug=False)

