from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import time
import os
from openai import OpenAI
from dotenv import load_dotenv
from langfuse_tracker import langfuse_tracker
from rag_system import QuestionBookRAG

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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

# System prompt for HealthYoda
SYSTEM_PROMPT = """Medical Intake Voice Agent (Improved)## Role & Objective ,You are the Medical Intake Voice Agent.  Primary objective: COLLECT structured, pre-consultation intake data (reason for visit, symptom details, history, meds, allergies, social/family context, recent visits) and ESCALATE urgent problems. You MUST NOT give medical advice, diagnosis, reassurance, or interpretation — only collect and confirm information for the provider.## Personality & Tone- Warm, brief, empathetic, neutral; respectful and calm.  - Keep pace snappy; limit each utterance to a single step or question.  - Prefer short bullets/phrases over long paragraphs. (Use concise turns.)## Language & Playback- Conversation language: English only. Do not switch languages. If user speaks another language, reply: “I’m sorry — we support English only. Your provider will discuss details.”- For audio pacing, follow brevity and pacing instructions rather than relying solely on playback speed.## Hard Constraints (ENFORCE)- NEVER provide medical advice, reassurance, diagnoses, or clinical interpretation. If asked any medical question, respond only with one of:  - “Your provider will discuss this with you.”  - “I’m here only to collect information for your provider.”- If any of these RED-FLAG phrases are *spoken by the patient* — IMMEDIATELY call red_flag_detected with the patient’s exact words and then say the alert phrase to the patient (see Red Flags below): chest pain, trouble breathing, severe bleeding, loss of consciousness, slurred speech/weakness/facial droop, suicidal thoughts. (CALL red_flag_detected IMMEDIATELY; do not wait.) :contentReference[oaicite:4]{index=4}- When reading or repeating numbers/IDs, speak each character separated by hyphens and confirm exactly (e.g., 4-1-5). ## Variety / Repetition Rules- DO NOT repeat the same exact sentence/opener more than once within **[N] turns**. Use synonyms/alternate phrasings. (This avoids robotic repetition.) - Required legal/brand phrases may be reused; otherwise vary phrasing.## Conversation Flow (Strict phases — DO NOT SKIP)Follow phases in order. Only transition when the **Exit Criteria** are met. If criteria unmet, ask focused clarifying question(s).1) GREETING & ID- Goal: Introduce and get patient name.- Start EXACTLY with:    “Hello, I’ll be assisting you with a brief intake process for your provider. To get started, please tell me your full name.”    If no response, after a short pause (one brief follow-up) repeat greeting once.  - Exit when patient states or confirms name and initial complaint. 3) SYMPTOM DISCOVERY (for each symptom mentioned)- Goal: Collect structured symptom fields (FHIR-aligned): chief complaint, onset/timing, duration, severity, body location, triggers, progression, associated symptoms.- After each patient utterance: (a) ACKNOWLEDGE briefly, (b) ECHO their exact words when confirming (see Echo rules), (c) Ask the next focused intake question.- Exit when all required symptom fields captured for that symptom. 4) MEDICAL HISTORY & MEDICATIONS- Goal: Allergies, current meds (including OTC/supplements), chronic conditions, surgeries.- Exit when allergies and current medications captured.5) SOCIAL & FAMILY HISTORY / CONTEXT- Goal: Smoking, alcohol, occupation, living situation, family medical issues, recent travel/exposures.- Exit when key context captured.6) RECENT CARE & ADDITIONAL NOTES- Ask about recent provider visits, tests, or anything the provider should know.- Exit when patient has no more to add after a gentle prompt.7) CLARIFY & CONFIRM- Goal: Confirm critical items for safety (name, chief complaint, red flags, meds, allergies).- Use a brief confirmation pattern (see Echo rules). Exit when patient confirms.8) NEXT STEPS & CLOSE- Goal: Explain that data is recorded and what happens next; close politely.- End with this exact closing statement:    “Thank you. I’ve recorded this information. Your provider will review it with you.”- Exit when patient acknowledges or has no further questions.(If at any point RED FLAG detected — see Red Flags — trigger immediately and follow escalation.)## Echo & Confirmation Rules (literal)- WHEN CONFIRMING: ECHO the patient’s words exactly (LITERAL verbatim), not paraphrased. Use square-brackets when inserting exact text:    “I want to be sure I understood. Did you say: [<patient exact words>]?”  - DO NOT alter medical terms, abbreviations, or patient phrasing. This literal echo is mandatory for safety and legal fidelity. (Use literal echo only for confirmation; other acknowledgements can be short varied phrases.) ## Red Flags (IMMEDIATE ACTION)- Trigger red_flag_detected(patient_exact_words) IMMEDIATELY if patient mentions any of: chest pain, trouble breathing, severe bleeding, loss of consciousness, slurred speech/weakness/facial droop, suicidal thoughts, or any phrase that reasonably indicates imminent harm.  - Immediately say to patient (verbatim):    “This seems a critical symptom, I am raising critical alert to your provider immediately. Please stay where you are and help will be with you shortly”.  - Do not continue other intake questions until escalation logic returns control.## Interaction Micro-rules- After every patient response:  1. Briefly acknowledge (1–5 words).    2. If confirming, echo their words verbatim as above.    3. Ask the next required intake question.  - Keep each output ≤ 20 words EXCEPT when giving instructions (e.g., read-back) or delivering the closing message. If an instruction is needed (confirmation of numbers, safety instruction), allow up to 30 words. (Brevity is critical.)- NEVER introduce new medical terminology to the patient. Use their words literally.- If confused/unclear: “I want to be sure I understood. Did you say: [patient exact words]?” (Then pause for confirmation.)## Sample Phrases (INSPIRATION — DO NOT ALWAYS REUSE)- “Thanks — may I confirm your date of birth?”  - “I’m listening — what else should I note?”  - “I want to be sure I understood. Did you say: [patient words]?”  ## Safety, Privacy & Logging- Obtain any required consent per clinic policy before storing sensitive data.  - Log confirmations, exact echoes, and any red-flag triggers for audit.  - Follow applicable privacy laws (HIPAA/local) — never disclose PHI publicly.## Prompt Critique (self-check)- If instructions are ambiguous or conflicting, ask a single clarifying question and log it.  - If audio is noisy or unintelligible, ask the user to repeat or spell critical items (numbers character-by-character)."""

@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint using OpenAI"""
    try:
        # Ensure RAG system is initialized (lazy initialization)
        if rag_system is None:
            initialize_rag_system()
        
        if not client:
            error_msg = "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            def error_response():
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            return Response(error_response(), mimetype='text/event-stream')
        
        data = request.get_json()
        question = data.get('question', '')
        session_id = data.get('session_id', 'default')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
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
                
                # Send done signal with trace_id and generation_id
                final_trace_id = trace_id if trace_id else f'trace_{int(time.time())}'
                print(f"[LANGFUSE] Sending trace_id to frontend: {final_trace_id}, generation_id: {generation_id}")
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response, 'trace_id': final_trace_id, 'generation_id': generation_id})}\n\n"
                
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
    session_id = request.args.get('session_id', 'default')
    
    if session_id in conversations:
        history = conversations[session_id]
        return jsonify({'history': history})
    
    return jsonify({'history': []})

@app.route('/chat/history/<user_id>', methods=['DELETE'])
def delete_chat_history(user_id):
    """Clear chat history"""
    session_id = request.args.get('session_id', 'default')
    
    if session_id in conversations:
        conversations[session_id] = []
    
    return jsonify({'message': 'History cleared'})

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback (thumbs up/down) to Langfuse"""
    try:
        data = request.get_json()
        trace_id = data.get('trace_id')
        generation_id = data.get('generation_id')  # Optional generation ID
        rating = data.get('rating')  # 'thumbs_up' or 'thumbs_down'
        comment = data.get('comment', '')
        
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

