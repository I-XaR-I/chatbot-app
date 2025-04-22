from flask import Flask, request, jsonify, Response, send_from_directory, send_file
from flask_cors import CORS
from ollama_client import OllamaClient
import os
import json
import threading
import time
import traceback
import subprocess
import requests
import logging
import sys
import platform
from typing import Dict, List, Any, Optional
from threading import RLock
from concurrent.futures import ThreadPoolExecutor

class SimpleCache:
    """A simple in-memory cache implementation."""
    
    def __init__(self, default_timeout=300):
        self.cache = {}
        self.timeouts = {}
        self.default_timeout = default_timeout
        self._lock = RLock()
    
    def get(self, key):
        """Look up key in the cache and return the value if it exists and hasn't expired."""
        with self._lock:
            if key not in self.cache:
                return None
            if key in self.timeouts:
                expiry = self.timeouts[key]
                if expiry is not None and expiry <= time.time():
                    del self.cache[key]
                    del self.timeouts[key]
                    return None
            return self.cache[key]
    
    def set(self, key, value, timeout=None):
        """Add a new key/value to the cache with optional expiry."""
        with self._lock:
            self.cache[key] = value
            if timeout is None:
                timeout = self.default_timeout
            if timeout > 0:
                self.timeouts[key] = time.time() + timeout
            else:
                self.timeouts[key] = None
            return True
    
    def delete(self, key):
        """Delete a key from the cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.timeouts:
                    del self.timeouts[key]
                return True
            return False
    
    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self.cache.clear()
            self.timeouts.clear()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()]
)
logger = logging.getLogger("chat_handler")

app = Flask(__name__)
CORS(app)

app.config['KEEP_ALIVE_TIMEOUT'] = 120

response_cache = SimpleCache(default_timeout=600)

worker_pool = ThreadPoolExecutor(max_workers=4)

ollama_server = os.environ.get("OLLAMA_SERVER", "http://localhost:11434")
print(f"Connecting to Ollama server at: {ollama_server}")

model_name = os.environ.get("MODEL_NAME", "")
print(f"Initial model setting: {model_name or 'Will select first available model'}")

FAST_MODE = os.environ.get("FAST_MODE", "0") == "1"
if FAST_MODE:
    print("⚡ FAST MODE ENABLED: Optimizing for speed over quality")

active_generations = {}

model_downloads = {}

model = None
model_loading = False
model_error = None

model_state = {
    "loaded": False,
    "loading": False,
    "instance": None,
    "last_used": 0,
    "error": None
}

def is_ollama_running() -> bool:
    """Check if Ollama service is currently running."""
    try:
        response = requests.get(f"{ollama_server}/api/version", timeout=2)
        if response.status_code == 200:
            logger.info("Ollama service is already running")
            return True
    except requests.exceptions.RequestException:
        logger.info("Ollama service is not running")
        return False
    return False

def find_ollama_executable() -> Optional[str]:
    """Find the Ollama executable path on Windows."""
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Ollama", "ollama.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Ollama", "ollama.exe"),
    ]
    
    for path in possible_paths:
        if os.path.isfile(path):
            logger.info(f"Found Ollama at: {path}")
            return path
    
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
        exe_file = os.path.join(path, "ollama.exe")
        if is_exe(exe_file):
            logger.info(f"Found Ollama in PATH: {exe_file}")
            return exe_file
    
    logger.error("Ollama executable not found. Please install Ollama first.")
    return None

def start_ollama_service() -> bool:
        
    try:
        if platform.system() == "Windows":
            ollama_path = find_ollama_executable()
            if not ollama_path:
                print("Please download and install Ollama from https://ollama.com/\n")
                return False
            
            logger.info(f"Starting Ollama from: {ollama_path}")
            print(f"\n🚀 Starting Ollama server from: {ollama_path}\n")
            
            subprocess.Popen([ollama_path, "serve"], 
                              creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            logger.info("Starting Ollama service with 'ollama serve'")
            print("\n🚀 Starting Ollama server...\n")
            
            subprocess.Popen(["ollama", "serve"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        
        print("Waiting for Ollama to start...")
        for i in range(15):
            time.sleep(1)
            print(f"Checking Ollama status ({i+1}/15)...")
            if is_ollama_running():
                logger.info("Ollama service started successfully")
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Failed to start Ollama service: {str(e)}")
        return False

if not is_ollama_running():
    logger.info("Ollama is not running, attempting to start it...")
    start_ollama_service()

def fetch_available_models():
    """Fetch available models directly from Ollama API"""
    try:
        response = requests.get(f"{ollama_server}/api/tags")
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            available_models = [m["name"] for m in models_data]
            print(f"Available models: {available_models}")
            return models_data, available_models
        else:
            print(f"Failed to fetch models from Ollama API: {response.status_code}")
            return [], []
    except Exception as e:
        print(f"Error fetching models from Ollama API: {e}")
        return [], []

def load_model_async():
    global model, model_loading, model_error, model_name
    try:
        print("Starting Ollama client initialization...")
        
        models_data, available_models = fetch_available_models()
        
        if not model_name:
            if available_models:
                model_name = available_models[0]
                print(f"No specific model requested, using first available: {model_name}")
            else:
                model_name = "llama2"
                print(f"No models available, falling back to default: {model_name}")
        
        temp_model = OllamaClient(
            model_name=model_name,
            base_url=ollama_server,
            fast_mode=FAST_MODE,
            cache_size=100
        )
        
        if models_data and model_name not in available_models:
            print(f"Warning: Model '{model_name}' not found in Ollama.")
            print(f"Available models: {available_models}")
            print(f"Ollama will automatically download '{model_name}' when first used.")
        
        model = temp_model
        model_state["instance"] = temp_model
        model_state["loaded"] = True
        model_state["loading"] = False
        model_state["last_used"] = time.time()
        model_state["error"] = None
        
        print(f"Ollama client initialized for model: {model_name}")
        model_error = None
            
    except Exception as e:
        print(f"Error initializing Ollama client: {e}")
        print(traceback.format_exc())
        model_error = str(e)
        model_state["error"] = str(e)
        model_state["loading"] = False
        
        if "Connection" in str(e) and "refused" in str(e):
            model_error = "Could not connect to Ollama server. Please make sure Ollama is installed and running.\n"
            model_error += "Visit https://ollama.com/ to download and install Ollama."
    finally:
        model_loading = False

print("Starting Ollama client in background...")
model_loading = True
loading_thread = threading.Thread(target=load_model_async)
loading_thread.daemon = True
loading_thread.start()

@app.route("/chat", methods=["POST"])
def chat():
    global model, model_loading, model_error
    
    if model:
        model_state["last_used"] = time.time()
    
    if model_loading:
        return jsonify({
            "error": "Ollama client is still initializing. Please try again in a moment.",
            "status": "loading"
        }), 503
    
    if model is None:
        if model_error:
            error_message = f"Failed to initialize Ollama client: {model_error}"
            suggestions = "Try:\n1. Make sure Ollama is installed and running\n2. Check the Ollama server URL\n3. Restart the server"
            return jsonify({
                "error": error_message,
                "suggestions": suggestions
            }), 500
        else:
            return jsonify({
                "error": "Ollama client not initialized. Please restart the server."
            }), 500
    
    user_input = request.json.get("message", "")
    stream_mode = request.json.get("stream", True)
    max_tokens = min(int(request.json.get("max_tokens", 512)), 6144)  # Increased from 1024 to 6144 (6x)
    
    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    request_id = str(time.time())
    active_generations[request_id] = {
        "status": "processing",
        "start_time": time.time()
    }
    
    cache_key = f"{model_name}:{user_input}:{max_tokens}"
    if not stream_mode:
        cached_response = response_cache.get(cache_key)
        if cached_response:
            print(f"Using cached response for: {user_input[:30]}...")
            active_generations[request_id]["status"] = "completed (cached)"
            active_generations[request_id]["end_time"] = time.time()
            
            processing_time = active_generations[request_id]["end_time"] - active_generations[request_id]["start_time"]
            
            return jsonify({
                "response": cached_response,
                "processing_time": f"{processing_time:.2f}s",
                "cached": True
            })
    
    try:
        if stream_mode:
            def generate_stream():
                try:
                    response_chunks = []
                    batch_chunk = ""
                    full_response = ""
                    
                    for chunk in model.stream(user_input, max_tokens=max_tokens):
                        batch_chunk += chunk
                        response_chunks.append(chunk)
                        full_response += chunk
                        
                        if len(response_chunks) >= 5:
                            yield f"data: {json.dumps({'chunk': batch_chunk})}\n\n"
                            batch_chunk = ""
                            response_chunks = []
                    
                    if batch_chunk:
                        yield f"data: {json.dumps({'chunk': batch_chunk})}\n\n"
                    
                    if full_response:
                        response_cache.set(cache_key, full_response)
                    
                    processing_time = time.time() - active_generations[request_id]["start_time"]
                    completion_data = {
                        'done': True, 
                        'processing_time': f'{processing_time:.2f}s'
                    }
                    
                    active_generations[request_id]["status"] = "completed"
                    active_generations[request_id]["end_time"] = time.time()
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    
                except Exception as e:
                    print(f"Streaming error: {e}")
                    active_generations[request_id]["status"] = "failed"
                    active_generations[request_id]["error"] = str(e)
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            headers = {
                'Content-Type': 'text/event-stream', 
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Transfer-Encoding': 'chunked'
            }
            return Response(generate_stream(), mimetype='text/event-stream', headers=headers)
        else:
            response = model.infer(user_input, max_tokens=max_tokens)
            
            response_cache.set(cache_key, response)
            
            active_generations[request_id]["status"] = "completed"
            active_generations[request_id]["end_time"] = time.time()
            
            processing_time = active_generations[request_id]["end_time"] - active_generations[request_id]["start_time"]
            
            result = {
                "response": response,
                "processing_time": f"{processing_time:.2f}s"
            }
                
            return jsonify(result)
    except Exception as e:
        print(f"Inference error: {e}")
        active_generations[request_id]["status"] = "failed"
        active_generations[request_id]["error"] = str(e)
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    global model, model_loading, model_error
    
    current_time = time.time()
    to_remove = []
    for req_id, data in active_generations.items():
        if current_time - data.get("start_time", 0) > 600:
            to_remove.append(req_id)
    
    for req_id in to_remove:
        del active_generations[req_id]
    
    available_models = []
    if model:
        try:
            models_data = model.list_models()
            available_models = [m["name"] for m in models_data]
        except Exception as e:
            print(f"Error fetching model list: {e}")
    
    status_info = {
        "model": model_name,
        "status": "loading" if model_loading else ("ready" if model else "not loaded"),
        "active_generations": len(active_generations),
        "fast_mode": FAST_MODE,
        "available_models": available_models,
        "server": ollama_server
    }
    
    if model_error:
        status_info["error"] = model_error
    
    return jsonify(status_info)

@app.route("/models", methods=["GET"])
def list_models():
    global model
    
    if not model:
        return jsonify({
            "error": "Ollama client not initialized"
        }), 503
    
    try:
        models = model.list_models()
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/change_model", methods=["POST"])
def change_model():
    global model, model_name
    
    if not model:
        return jsonify({
            "error": "Ollama client not initialized"
        }), 503
    
    new_model = request.json.get("model")
    if not new_model:
        return jsonify({"error": "Model name is required"}), 400
    
    try:
        model.model_name = new_model
        model_name = new_model
        return jsonify({"success": True, "model": new_model})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/list", methods=["GET"])
def list_available_models():
    """Return the list of available models from ollama_models.json"""
    try:
        with open("ollama_models.json", "r", encoding="utf-8") as f:
            models_data = json.load(f)
        return jsonify({"models": models_data})
    except Exception as e:
        print(f"Error loading models list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/models/download", methods=["POST"])
def download_model():
    """Start downloading a model using ollama pull"""
    model_name = request.json.get("model")
    if not model_name:
        return jsonify({"error": "Model name is required"}), 400
    
    active_downloads = [d for d in model_downloads.values() if d.get("status") == "downloading"]
    if active_downloads:
        return jsonify({
            "error": "Another download is already in progress", 
            "current_download": active_downloads[0]
        }), 409
    
    download_id = f"dl_{time.time()}"
    model_downloads[download_id] = {
        "model": model_name,
        "status": "downloading",
        "progress": 0,
        "start_time": time.time()
    }
    
    download_thread = threading.Thread(
        target=download_model_thread,
        args=(download_id, model_name)
    )
    download_thread.daemon = True
    download_thread.start()
    
    return jsonify({
        "download_id": download_id,
        "model": model_name,
        "status": "started"
    })

def download_model_thread(download_id, model_name):
    """Background thread to download a model and track progress"""
    try:
        print(f"Starting download for: {model_name}")
        
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in process.stdout:
            try:
                if "pulling" in line.lower() and "%" in line:
                    try:
                        progress_str = line.split("%")[0].split(" ")[-1].strip()
                        progress = float(progress_str)
                        model_downloads[download_id]["progress"] = progress
                    except ValueError:
                        print(f"Could not parse progress from line: {line.strip()}")
                
                print(f"Ollama pull output: {line.strip()}")
            
            except Exception as e:
                print(f"Error processing output line: {str(e)}")
                continue
        
        return_code = process.wait()
        
        if return_code == 0:
            model_downloads[download_id]["status"] = "completed"
            model_downloads[download_id]["progress"] = 100
            print(f"Download of {model_name} completed successfully")
        else:
            model_downloads[download_id]["status"] = "failed"
            model_downloads[download_id]["error"] = f"Process exited with code {return_code}"
            print(f"Download of {model_name} failed with code {return_code}")
    
    except Exception as e:
        model_downloads[download_id]["status"] = "failed"
        model_downloads[download_id]["error"] = f"Download error: {str(e)}"
        print(f"Error downloading model {model_name}: {e}")
        print(traceback.format_exc())

@app.route("/models/download/status", methods=["GET"])
def get_download_status():
    """Get the status of all model downloads"""
    current_time = time.time()
    to_remove = []
    for dl_id, dl_info in model_downloads.items():
        if dl_info.get("status") != "downloading" and current_time - dl_info.get("start_time", 0) > 3600:
            to_remove.append(dl_id)
    
    for dl_id in to_remove:
        del model_downloads[dl_id]
    
    return jsonify({"downloads": model_downloads})

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "Server is running", 
        "model_status": "loading" if model_loading else ("ready" if model else "not loaded"),
        "model": model_name,
        "ollama_server": ollama_server
    })

@app.route("/frontend/<path:path>")
def serve_frontend(path):
    return send_from_directory("../frontend", path)
    
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return send_file("../frontend/static/index.html")

@app.route("/models/available", methods=["GET"])
def available_models():
    """Return the list of available models directly from Ollama API"""
    try:
        models_data, _ = fetch_available_models()
        return jsonify({"models": models_data})
    except Exception as e:
        print(f"Error loading models list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/models/current", methods=["GET"])
def get_current_model():
    """Return the currently loaded model"""
    return jsonify({"model": model_name})

def keep_model_warm():
    """Periodically ping the model to keep it loaded in memory"""
    while True:
        try:
            time.sleep(300)
            
            if model_state["loaded"] and (time.time() - model_state["last_used"]) > 600:
                print("Keeping model warm with test request...")
                model.infer("Hello", max_tokens=10)
                model_state["last_used"] = time.time()
                
        except Exception as e:
            print(f"Error in keep_model_warm: {e}")

warming_thread = threading.Thread(target=keep_model_warm, daemon=True)
warming_thread.start()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STARTING FLASK SERVER ON PORT 5000")
    print("="*60)
    print("Open your browser to: http://localhost:5000")
    print(f"Using Ollama with model: {model_name}")
    print("Make sure Ollama is installed and running")
    print("Visit https://ollama.com/ if you need to install Ollama")
    print("="*60 + "\n")
    
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    except Exception as e:
        print(f"ERROR STARTING SERVER: {e}")
        print("This might be caused by another application using port 5000.")
        print("Try stopping other applications or changing the port number in this file.")
