import os
import json
import requests
import time
from typing import Dict, List, Generator, Optional, Any, Union
from functools import lru_cache

class OllamaClient:
    def __init__(self, model_name="llama2", base_url="http://localhost:11434", fast_mode=False, cache_size=50):
        self.model_name = model_name
        self.base_url = base_url
        self.api_generate_url = f"{base_url}/api/generate"
        self.api_chat_url = f"{base_url}/api/chat"
        self._ctx_size = 1024
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=3
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        self._session.headers.update({
            'Connection': 'keep-alive'
        })
        self.cache_size = cache_size
        if cache_size > 0:
            self.infer = self._cache_decorator(self.infer)
        try:
            response = self._session.get(f"{base_url}/api/version", timeout=1)
            if response.status_code == 200:
                version_info = response.json()
                print(f"Connected to Ollama server version {version_info.get('version')}")
            else:
                print(f"Warning: Ollama server returned status code {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"Warning: Could not connect to Ollama server at {base_url}")
            print("Please ensure Ollama is installed and running.")
            print("Visit https://ollama.com/ for installation instructions.")
    
    def _cache_decorator(self, func):
        @lru_cache(maxsize=self.cache_size)
        def cached_request(prompt, max_tokens, temperature):
            return func(prompt, max_tokens, temperature)
        
        def wrapper(prompt, max_tokens=1024, temperature=0.7):
            return cached_request(prompt, max_tokens, temperature)
            
        return wrapper
    
    def list_models(self) -> List[Dict[str, str]]:
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                return response.json().get("models", [])
            else:
                print(f"Error listing models: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def _format_prompt(self, text: str) -> str:
        return text.strip()
    
    def infer(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        formatted_prompt = self._format_prompt(prompt)
        try:
            params = {
                "model": self.model_name,
                "prompt": formatted_prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "options": {
                    "num_ctx": self._ctx_size,
                    "num_thread": 4
                }
            }
            response = self._session.post(
                self.api_generate_url, 
                json=params, 
                timeout=30,
                stream=True
            )
            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                        if chunk.get("done", False):
                            break
                return full_response.strip()
            else:
                return f"Error: Ollama API returned status code {response.status_code}"
        except Exception as e:
            print(f"Error during inference: {e}")
            return f"Error: {str(e)}"
    
    def stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> Generator[str, None, None]:
        formatted_prompt = self._format_prompt(prompt)
        try:
            params = {
                "model": self.model_name,
                "prompt": formatted_prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": True,
                "options": {
                    "num_ctx": self._ctx_size,
                    "num_thread": 4,
                    "seed": int(time.time())
                }
            }
            with self._session.post(
                self.api_generate_url, 
                json=params, 
                stream=True, 
                timeout=30
            ) as response:
                if response.status_code == 200:
                    buffer = []
                    buffer_size = 5
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("response", "")
                                if token:  
                                    buffer.append(token)
                                    if len(buffer) >= buffer_size:
                                        yield ''.join(buffer)
                                        buffer = []
                                if chunk.get("done", False):
                                    if buffer:
                                        yield ''.join(buffer)
                                    break
                            except json.JSONDecodeError:
                                print(f"Error parsing JSON: {line}")
                    if buffer:
                        yield ''.join(buffer)
                else:
                    yield f"Error: Ollama API returned status code {response.status_code}"
        except Exception as e:
            print(f"Error during streaming: {e}")
            yield f"Error: {str(e)}"

    def chat(self, 
             messages: List[Dict[str, str]], 
             temperature: float = 0.7, 
             max_tokens: int = 2048) -> Dict[str, Any]:
        try:
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "options": {
                    "num_ctx": 2048,
                    "num_predict": max_tokens
                }
            }
            response = requests.post(self.api_chat_url, json=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: Ollama API returned status code {response.status_code}")
                return {"message": {"content": f"Error: API returned status code {response.status_code}"}}
        except Exception as e:
            print(f"Error during chat: {e}")
            return {"message": {"content": f"Error: {str(e)}"}}
    
    def stream_chat(self, 
                   messages: List[Dict[str, str]], 
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> Generator[str, None, None]:
        try:
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "options": {
                    "num_ctx": 2048,
                    "num_predict": max_tokens
                }
            }
            with requests.post(self.api_chat_url, json=params, stream=True) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                print(f"Error parsing JSON: {line}")
                else:
                    yield f"Error: Ollama API returned status code {response.status_code}"
        except Exception as e:
            print(f"Error during streaming chat: {e}")
            yield f"Error: {str(e)}"
