"""
Ollama Client for HYoda - Replaces OpenAI API calls
Provides compatibility layer for easy migration from OpenAI to Ollama
"""
import requests
import json
import os
from typing import List, Dict, Generator, Optional

class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, host: str = None, model: str = None):
        self.host = host or os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'alibayram/medgemma:4b')
        self.api_url = f"{self.host}/api"
        
    def chat_completions_create(self, messages: List[Dict], stream: bool = False, 
                               temperature: float = 0.7, max_tokens: int = 1000):
        """
        Create chat completion (compatible with OpenAI API format)
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream responses
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generator yielding response chunks if stream=True, else complete response
        """
        # Convert OpenAI-style messages to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                stream=stream,
                timeout=300
            )
            response.raise_for_status()
            
            if stream:
                return self._stream_response(response)
            else:
                result = response.json()
                return self._format_response(result)
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ollama API request failed: {e}")
            raise
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert OpenAI messages format to Ollama prompt"""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}\n")
            elif role == 'user':
                prompt_parts.append(f"User: {content}\n")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}\n")
        
        # Add final prompt for assistant to respond
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def _stream_response(self, response) -> Generator:
        """Stream response chunks (compatible with OpenAI format)"""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        # Format as OpenAI-style chunk
                        yield type('obj', (object,), {
                            'choices': [type('obj', (object,), {
                                'delta': type('obj', (object,), {
                                    'content': chunk['response']
                                })()
                            })()]
                        })()
                except json.JSONDecodeError:
                    continue
    
    def _format_response(self, result: Dict):
        """Format Ollama response to match OpenAI structure"""
        return type('obj', (object,), {
            'choices': [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': result.get('response', '')
                })()
            })()]
        })()
    
    def embeddings_create(self, input_text: str, model: str = None):
        """
        Create embeddings (compatible with OpenAI format)
        
        Args:
            input_text: Text to embed (can be string or list)
            model: Model to use for embeddings
            
        Returns:
            Response with embeddings in OpenAI format
        """
        embed_model = model or "nomic-embed-text"  # Default embedding model for Ollama
        
        # Handle list or string input
        texts = [input_text] if isinstance(input_text, str) else input_text
        
        embeddings_list = []
        for text in texts:
            payload = {
                "model": embed_model,
                "prompt": text
            }
            
            try:
                response = requests.post(
                    f"{self.api_url}/embeddings",
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                embeddings_list.append(result.get('embedding', []))
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Ollama embeddings failed: {e}")
                raise
        
        # Format as OpenAI-style response
        return type('obj', (object,), {
            'data': [type('obj', (object,), {
                'embedding': emb
            })() for emb in embeddings_list]
        })()
    
    def test_connection(self) -> bool:
        """Test if Ollama is accessible"""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get('models', [])
            print(f"[OK] Ollama connected. Available models: {[m['name'] for m in models]}")
            return True
        except Exception as e:
            print(f"[ERROR] Cannot connect to Ollama at {self.host}: {e}")
            return False


# Global client instance
_ollama_client = None

def get_ollama_client(host: str = None, model: str = None) -> OllamaClient:
    """Get or create global Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient(host, model)
    return _ollama_client

