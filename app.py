from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import json
import time
import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from langfuse_tracker import langfuse_tracker
from rag_system import QuestionBookRAG

# Load environment variables from .env file
load_dotenv()

# Import HealthBench evaluation modules
try:
    # Add local evals folder to path
    evals_path = Path(__file__).resolve().parent / 'evals'
    sys.path.insert(0, str(evals_path))
    
    # Import evaluation modules from local evals folder
    from simple_live_evaluator import get_live_evaluator
    from helm_live_evaluator import get_helm_evaluator  # HELM-style evaluation
    from langfuse_scorer import create_langfuse_scorer
    from results_storage import get_results_storage
    
    EVALUATION_AVAILABLE = True
    print("✅ HealthBench evaluation modules loaded from local evals folder")
except Exception as e:
    EVALUATION_AVAILABLE = False
    print(f"[WARNING] HealthBench evaluation not available: {e}")
    import traceback
    traceback.print_exc()

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
# It will be None if LANGFUSE_ENABLED=false or if credentials are missing
langfuse = langfuse_tracker.client

# Initialize RAG system for Question Book with OpenAI client for embeddings
# Skip initialization in Flask reloader process (only initialize once in main process)
rag_system = None
live_evaluator = None
helm_evaluator = None
langfuse_scorer = None
results_storage = None

def initialize_rag_system():
    """Initialize RAG system (called once, not on reload)"""
    global rag_system
    if rag_system is None:
        try:
            rag_system = QuestionBookRAG('docx/Question BOOK.docx', openai_client=client)
            print(f"[OK] RAG System loaded: {len(rag_system.questions)} questions available")
            if rag_system.collection and rag_system.collection.count() > 0:
                print(f"[OK] Vector database ready: {rag_system.collection.count()} embeddings available")
            elif rag_system.collection:
                print(f"[INFO] Vector database initialized (no embeddings yet)")
        except Exception as e:
            print(f"[WARNING] Could not load RAG system: {e}")
            import traceback
            traceback.print_exc()
            rag_system = None

def initialize_evaluation_system():
    """Initialize HealthBench and HELM evaluation systems (called once, not on reload)"""
    global live_evaluator, helm_evaluator, langfuse_scorer, results_storage
    
    if not EVALUATION_AVAILABLE:
        print("[INFO] Evaluation system not available")
        return
    
    if live_evaluator is None:
        try:
            # Get grader model from environment or use default
            grader_model = os.getenv('HEALTHBENCH_GRADER_MODEL', 'gpt-4o-mini')
            helm_judge_model = os.getenv('HELM_JUDGE_MODEL', 'gpt-4o-mini')
            
            # Initialize HealthBench evaluator
            live_evaluator = get_live_evaluator(grader_model=grader_model)
            
            # Initialize HELM evaluator
            helm_evaluator = get_helm_evaluator(judge_model=helm_judge_model)
            
            # Initialize Langfuse scorer with the existing langfuse client
            # Will auto-disable if langfuse is None
            langfuse_scorer = create_langfuse_scorer(langfuse_client=langfuse)
            
            # Initialize results storage for custom dashboard
            results_storage = get_results_storage()
            
            if live_evaluator.enabled:
                print(f"[OK] HealthBench evaluation initialized (grader: {grader_model})")
            if helm_evaluator and helm_evaluator.enabled:
                print(f"[OK] HELM evaluation initialized (judge: {helm_judge_model})")
            if results_storage:
                print(f"[OK] Results storage initialized for custom dashboard")
            
            if not live_evaluator.enabled and (not helm_evaluator or not helm_evaluator.enabled):
                print("[INFO] All evaluation systems disabled")
        except Exception as e:
            print(f"[WARNING] Could not initialize evaluation system: {e}")
            import traceback
            traceback.print_exc()
            live_evaluator = None
            langfuse_scorer = None
            results_storage = None

# Initialize RAG system (no need for complex process detection since debug=False)
# With debug=False, Flask runs in a single process, so initialization happens once
initialize_rag_system()
initialize_evaluation_system()

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
            generation_id = None  # Initialize generation_id
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
                
                # ===================================================================
                # DUAL EVALUATION: HealthBench + HELM in parallel
                # ===================================================================
                eval_results = None
                helm_results = None
                
                # Get medical context from RAG
                medical_context = rag_question_info.get('tree_path') if rag_question_info else None
                
                # HEALTHBENCH EVALUATION
                if live_evaluator and live_evaluator.enabled:
                    try:
                        print("[EVALUATION] Starting HealthBench evaluation...")
                        
                        # Evaluate the bot's response
                        eval_results = live_evaluator.evaluate(
                            conversation_history=conversation_history[:-1],  # Exclude the response we're evaluating
                            bot_question=full_response,
                            medical_context=medical_context
                        )
                        
                        if eval_results:
                            # Display evaluation results
                            print(f"[EVALUATION] [OK] Overall Score: {eval_results.overall_score:.2f} "
                                  f"({eval_results.metrics.get('rubrics_passed', 0)}/"
                                  f"{eval_results.metrics.get('num_rubrics_evaluated', 0)} passed)")
                            
                            # Display safety score
                            safety_score = eval_results.safety_score
                            print(f"[EVALUATION] [OK] Safety Score: {safety_score:.2f}")
                            
                            # Display tag scores
                            if eval_results.tag_scores:
                                tag_scores_str = ", ".join([f"{tag}: {score:.2f}" 
                                                            for tag, score in eval_results.tag_scores.items()])
                                print(f"[EVALUATION] Tag Scores: {tag_scores_str}")
                            
                            # Display red flags if any
                            if eval_results.red_flags:
                                print(f"[EVALUATION] [WARNING] {len(eval_results.red_flags)} RED FLAG(S) DETECTED:")
                                for flag in eval_results.red_flags:
                                    print(f"[EVALUATION]   [{flag['severity']}] {flag['criterion']}")
                                    print(f"[EVALUATION]   Reason: {flag['explanation'][:100]}...")
                            
                            # Display critical failure alert
                            if eval_results.critical_failure:
                                print(f"[EVALUATION] [ALERT] CRITICAL SAFETY VIOLATION DETECTED!")
                            
                            # Log scores to Langfuse
                            if langfuse_scorer and trace_id:
                                langfuse_scorer.log_scores(
                                    trace_id=trace_id,
                                    generation_id=generation_id,
                                    eval_results=eval_results,
                                    medical_context=medical_context
                                )
                        else:
                            print("[EVALUATION] [WARNING] Evaluation returned no results")
                            
                    except Exception as eval_error:
                        print(f"[EVALUATION] [WARNING] HealthBench evaluation failed: {eval_error}")
                        import traceback
                        traceback.print_exc()
                
                # HELM EVALUATION (in parallel)
                if helm_evaluator and helm_evaluator.enabled:
                    try:
                        print("[HELM] Starting HELM evaluation...")
                        
                        # Evaluate with HELM criteria
                        helm_results = helm_evaluator.evaluate(
                            conversation_history=conversation_history[:-1],
                            bot_response=full_response,
                            medical_context=medical_context
                        )
                        
                        if helm_results:
                            print(f"[HELM] [OK] Overall: {helm_results.overall_helm_score:.2f}/5.0")
                            print(f"[HELM] Accuracy: {helm_results.accuracy_score}/5, "
                                  f"Completeness: {helm_results.completeness_score}/5, "
                                  f"Clarity: {helm_results.clarity_score}/5")
                            print(f"[HELM] Empathy: {helm_results.empathy_score}/5, "
                                  f"Safety: {helm_results.safety_score}/5, "
                                  f"Relevance: {helm_results.relevance_score}/5")
                        else:
                            print("[HELM] [WARNING] HELM evaluation returned no results")
                    
                    except Exception as helm_error:
                        print(f"[HELM] [WARNING] HELM evaluation failed: {helm_error}")
                        import traceback
                        traceback.print_exc()
                
                # Save combined results to storage
                if results_storage and (eval_results or helm_results):
                    try:
                        # Combine HealthBench and HELM results
                        combined_eval = {}
                        
                        if eval_results:
                            combined_eval = eval_results.to_dict()
                        
                        if helm_results:
                            combined_eval['helm'] = helm_results.to_dict()
                        
                        results_storage.save_evaluation(
                            eval_result=combined_eval,
                            conversation_id=session_id,
                            user_message=question,
                            bot_response=full_response,
                            medical_context=medical_context
                        )
                    except Exception as storage_error:
                        print(f"[WARNING] Failed to save combined results: {storage_error}")
                # ===================================================================
                
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

@app.route('/healthbench/results', methods=['GET'])
def get_healthbench_results():
    """
    API endpoint to get HealthBench evaluation results for dashboard.
    
    Query Parameters:
        limit (int): Maximum number of results to return (default: 50)
        
    Returns:
        JSON with evaluation results and statistics
    """
    try:
        if not results_storage:
            return jsonify({
                'error': 'HealthBench evaluation not available',
                'results': [],
                'statistics': {}
            }), 503
        
        # Get limit from query parameters
        limit = request.args.get('limit', 50, type=int)
        
        # Get recent results
        recent_results = results_storage.get_recent_evaluations(limit=limit)
        
        # Get statistics
        statistics = results_storage.get_statistics()
        
        return jsonify({
            'success': True,
            'results': recent_results,
            'statistics': statistics,
            'total_count': len(recent_results)
        })
    
    except Exception as e:
        print(f"[ERROR] Failed to retrieve HealthBench results: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'results': [],
            'statistics': {}
        }), 500


@app.route('/healthbench/dashboard', methods=['GET'])
def healthbench_dashboard():
    """
    Serve the HealthBench evaluation dashboard HTML page.
    """
    try:
        # Serve the dashboard HTML file
        dashboard_path = Path(__file__).parent / 'healthbench_dashboard.html'
        
        if not dashboard_path.exists():
            return f"<h1>Dashboard not found</h1><p>Please ensure healthbench_dashboard.html exists in the HYoda folder.</p>", 404
        
        return send_file(dashboard_path)
    
    except Exception as e:
        print(f"[ERROR] Failed to serve dashboard: {e}")
        return f"<h1>Error loading dashboard</h1><p>{str(e)}</p>", 500

if __name__ == '__main__':
    # Only print startup messages once (not on reload)
    # RAG system is initialized above based on process detection
    
    if not hasattr(app, '_startup_printed'):
        print("Starting HealthYoda chatbot server...")
        print("Server will run on http://127.0.0.1:8002")
        print("-" * 50)
        
        if not openai_api_key:
            print("\n[WARNING] OPENAI_API_KEY not set!")
            print("Set it using: export OPENAI_API_KEY='your-api-key'")
            print("Or create a .env file with OPENAI_API_KEY=your-api-key")
            print("The chatbot will not work without an API key.\n")
        else:
            print("[OK] OpenAI API key found!")
        
        if not langfuse:
            print("[WARNING] Langfuse keys not found. Traces will not be logged.")
            print("Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST in .env")
        else:
            print("[OK] Langfuse configured! Traces will be logged.")
            print(f"   Using Langfuse tracker module for observability")
        
        # Show HealthBench dashboard status
        if results_storage:
            print("[OK] HealthBench Dashboard: http://127.0.0.1:8002/healthbench/dashboard")
            print("   View real-time evaluation scores and metrics")
        
        print("-" * 50)
        app._startup_printed = True
    
    app.run(host='127.0.0.1', port=8002, debug=False)

