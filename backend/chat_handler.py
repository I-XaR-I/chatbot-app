from flask import Flask, request, jsonify, Response, send_from_directory, send_file
from flask_cors import CORS
from model_loader import DeepSeekModel
import os
import json
import threading
import time
import traceback

app = Flask(__name__)
CORS(app)

# Get model name from reference file
model_name = "deepseek-ai/deepseek-r1-distill-llama-8b"  # Default
model_path = ""
reference_path = os.environ.get("ENGINE_PATH", "../models/model_reference.json")
if os.path.exists(reference_path):
    try:
        with open(reference_path, "r") as f:
            reference_data = json.load(f)
            model_name = reference_data["model_name"]
            model_path = reference_data.get("gguf_path", "")
    except Exception as e:
        print(f"Error reading model reference: {e}")

# Check for CPU-only mode and consider using smaller model
cpu_only = False
try:
    import torch
    cpu_only = not torch.cuda.is_available()
    if cpu_only:
        print("CPU-ONLY MODE DETECTED: Will use smaller model for better performance")
        # Default to smaller model in CPU mode
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
except:
    print("Cannot detect GPU status. Assuming CPU-only mode.")
    cpu_only = True

# Enable fast mode for quicker responses
FAST_MODE = os.environ.get("FAST_MODE", "0") == "1"  # Default to disabled
if FAST_MODE:
    print("⚡ FAST MODE ENABLED: Optimizing for speed over quality")

# Track ongoing generations
active_generations = {}

# Add CUDA check before loading model
def check_cuda_status():
    try:
        # Check if CUDA_PATH is valid
        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path and not os.path.exists(os.path.join(cuda_path, "bin")):
            print(f"WARNING: CUDA_PATH is set to invalid directory: {cuda_path}")
            print("Run fix_dependencies.py to correct this issue")
            return False
            
        # Optional: Try to detect if CUDA is installed but not properly configured
        if not cuda_path:
            possible_paths = [
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"Found CUDA at {path} but CUDA_PATH is not set")
                    print("Run fix_dependencies.py to correct this issue")
                    return False
        return True
    except Exception as e:
        print(f"Error checking CUDA status: {e}")
        return False

# Check CUDA before starting model loading
cuda_status_ok = check_cuda_status()
if not cuda_status_ok:
    print("WARNING: CUDA configuration issues detected")
    print("The model will likely run in CPU mode (slower)")

# Load the model
model = None
model_loading = False
model_error = None

def load_model_async():
    global model, model_loading, model_error
    try:
        print("Starting model loading process...")
        
        # Check for CUDA issues before loading
        try:
            import torch
            if torch.cuda.is_available():
                print(f"Using GPU: {torch.cuda.get_device_name(0)}")
                
                # Check GPU memory
                free_memory = torch.cuda.mem_get_info()[0] / (1024**3)  # Convert to GB
                print(f"Free GPU memory: {free_memory:.2f} GB")
                
                if (free_memory < 2.0):  # Less than 2GB free
                    print("WARNING: Very little GPU memory available!")
                    print("The model may fail to load with CUDA acceleration.")
        except Exception as e:
            print(f"CUDA check error: {e}")
        
        # Try to load model with a timeout guard to prevent hanging
        import threading
        import _thread
        
        def timeout_handler():
            print("ERROR: Model loading timed out after 300 seconds!")
            print("This usually indicates a CUDA or memory issue.")
            # Force exit the thread
            _thread.interrupt_main()
        
        # Set timeout for model loading (5 minutes)
        timer = threading.Timer(300, timeout_handler)
        timer.daemon = True
        timer.start()
        
        try:
            temp_model = DeepSeekModel(
                model_path,  # Use the GGUF path from reference
                model_name=model_name,
                fast_mode=FAST_MODE
            )
            # Cancel timeout
            timer.cancel()
            
            model = temp_model
            print(f"Model loaded successfully: {model_name}")
            print(f"Using GGUF format with llama.cpp")
            model_error = None
        except Exception as load_error:
            timer.cancel()
            raise load_error
            
    except KeyboardInterrupt:
        print("Model loading was interrupted by timeout!")
        model_error = "Loading timed out after 300 seconds - possible CUDA memory issue"
    except Exception as e:
        print(f"Error loading model: {e}")
        print(traceback.format_exc())
        model_error = str(e)
        
        # Check for specific error types and add helpful messages
        error_str = str(e).lower()
        if "cuda" in error_str and "out of memory" in error_str:
            model_error += "\n\nThis is a GPU memory issue. Try:\n1. Close other applications\n2. Use a smaller model\n3. Force CPU mode by setting LLAMA_CUBLAS=0"
        elif "cublas64" in error_str or "cudart64" in error_str:
            model_error += "\n\nThis is a CUDA library issue. Try running fix_dependencies.py to correct CUDA paths."
    finally:
        model_loading = False

# Start loading model in background
print("Starting model loading in background...")
model_loading = True
loading_thread = threading.Thread(target=load_model_async)
loading_thread.daemon = True
loading_thread.start()

@app.route("/chat", methods=["POST"])
def chat():
    global model, model_loading, model_error
    
    if model_loading:
        return jsonify({
            "error": "Model is still loading. Please try again in a moment.",
            "status": "loading"
        }), 503
    
    if model is None:
        if model_error:
            # Provide more helpful error message
            error_message = f"Model failed to load: {model_error}."
            suggestions = "Try:\n1. Run gpu_diagnostic.py to check GPU setup\n2. Use a smaller model\n3. Restart the server"
            return jsonify({
                "error": error_message,
                "suggestions": suggestions
            }), 500
        else:
            return jsonify({
                "error": "Model not loaded. Please restart the server."
            }), 500
    
    user_input = request.json.get("message", "")
    stream_mode = request.json.get("stream", False)  # New parameter for streaming mode
    fast_response = request.json.get("fast", FAST_MODE)  # Allow per-request override
    include_thoughts = request.json.get("include_thoughts", False)  # New parameter for thoughts
    
    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    # Generate a unique ID for this request
    request_id = str(time.time())
    active_generations[request_id] = {
        "status": "processing",
        "start_time": time.time(),
        "fast_mode": fast_response  # Track whether fast mode was used
    }
    
    try:
        # Update model's fast mode setting for this request
        # Only change the setting if it's different from current setting
        if hasattr(model, 'fast_mode') and model.fast_mode != fast_response:
            print(f"Changing fast mode from {model.fast_mode} to {fast_response} for this request")
            model.fast_mode = fast_response
        
        if stream_mode:
            # Return streaming response for real-time updates
            def generate_stream():
                try:
                    # Generate thoughts first if requested
                    thoughts = None
                    if include_thoughts:
                        thoughts = model.generate_thoughts(user_input)
                        # Stream the thoughts as separate chunks if available
                        if thoughts:
                            for chunk in thoughts.split('\n'):
                                if chunk.strip():  # Only send non-empty chunks
                                    yield f"data: {json.dumps({'thought_chunk': chunk + '\n'})}\n\n"
                    
                    # Now stream the main response
                    for chunk in model.stream(user_input):
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
                    # Send final completion signal with thoughts
                    processing_time = time.time() - active_generations[request_id]["start_time"]
                    completion_data = {
                        'done': True, 
                        'processing_time': f'{processing_time:.2f}s'
                    }
                    
                    # Add thoughts to completion data if not streamed earlier
                    if include_thoughts and not thoughts:
                        completion_data['thoughts'] = model.generate_thoughts(user_input)
                    
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    active_generations[request_id]["status"] = "completed"
                    active_generations[request_id]["end_time"] = time.time()
                except Exception as e:
                    print(f"Streaming error: {e}")
                    print(traceback.format_exc())
                    active_generations[request_id]["status"] = "failed"
                    active_generations[request_id]["error"] = str(e)
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return Response(generate_stream(), mimetype='text/event-stream')
        else:
            # Standard non-streaming response
            response = model.infer(user_input)
            
            # Generate thoughts if requested
            thoughts = None
            if include_thoughts:
                thoughts = model.generate_thoughts(user_input)
            
            active_generations[request_id]["status"] = "completed"
            active_generations[request_id]["end_time"] = time.time()
            
            processing_time = active_generations[request_id]["end_time"] - active_generations[request_id]["start_time"]
            
            result = {
                "response": response,
                "processing_time": f"{processing_time:.2f}s",
                "fast_mode": fast_response
            }
            
            if include_thoughts:
                result["thoughts"] = thoughts
                
            return jsonify(result)
    except Exception as e:
        print(f"Inference error: {e}")
        print(traceback.format_exc())
        active_generations[request_id]["status"] = "failed"
        active_generations[request_id]["error"] = str(e)
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    global model, model_loading, model_error
    
    # Clean up old generations (older than 10 minutes)
    current_time = time.time()
    to_remove = []
    for req_id, data in active_generations.items():
        if current_time - data.get("start_time", 0) > 600:  # 10 minutes
            to_remove.append(req_id)
    
    for req_id in to_remove:
        del active_generations[req_id]
    
    # Return current status
    status_info = {
        "model": model_name,
        "status": "loading" if model_loading else ("ready" if model else "not loaded"),
        "active_generations": len(active_generations),
        "fast_mode": FAST_MODE
    }
    
    if model_error:
        status_info["error"] = model_error
    
    try:
        if model:
            import torch
            status_info["device"] = "GPU" if torch.cuda.is_available() else "CPU"
    except:
        status_info["device"] = "unknown"
    
    return jsonify(status_info)

# Add a simple root route for health checks
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Server is running", "model_status": "loading" if model_loading else ("ready" if model else "not loaded")})

# Add a route for the frontend static files
@app.route("/frontend/<path:path>")
def serve_frontend(path):
    return send_from_directory("../frontend", path)
    
# Add a catch-all route to serve the main index.html
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return send_file("../frontend/static/index.html")

if __name__ == "__main__":
    # Print clear server starting message
    print("\n" + "="*60)
    print("STARTING FLASK SERVER ON PORT 5000")
    print("="*60)
    print("Open your browser to: http://localhost:5000")
    print("The model will continue loading in the background")
    print("="*60 + "\n")
    
    try:
        # Use threaded=True to handle multiple requests
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    except Exception as e:
        print(f"ERROR STARTING SERVER: {e}")
        print("This might be caused by another application using port 5000.")
        print("Try stopping other applications or changing the port number in this file.")
