import os
import json
import time
from datetime import datetime

# Add error handling for CUDA path issues
try:
    # Check if CUDA_PATH exists and is valid before importing llama_cpp
    if "CUDA_PATH" in os.environ:
        cuda_path = os.environ["CUDA_PATH"]
        if not os.path.exists(os.path.join(cuda_path, "bin")):
            print(f"Warning: CUDA_PATH points to non-existent directory: {cuda_path}")
            print("Temporarily unsetting CUDA_PATH to avoid errors...")
            cuda_path_original = os.environ["CUDA_PATH"]
            del os.environ["CUDA_PATH"]
            print("Will attempt to use CPU mode instead")
        else:
            print(f"Using CUDA installation at: {cuda_path}")
    else:
        # Try to find CUDA installation in common locations
        possible_cuda_paths = [
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8",  # User's specific CUDA version
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0",
        ]
        
        for path in possible_cuda_paths:
            if os.path.exists(os.path.join(path, "bin")):
                print(f"Found valid CUDA installation at: {path}")
                print("Setting CUDA_PATH environment variable temporarily...")
                os.environ["CUDA_PATH"] = path
                break
    
    # Add memory check before importing llama_cpp
    try:
        import torch
        if torch.cuda.is_available():
            # Get available GPU memory
            device = torch.cuda.current_device()
            available_memory = torch.cuda.get_device_properties(device).total_memory
            available_gb = available_memory / (1024**3)
            print(f"GPU Memory: {available_gb:.2f} GB available")
            
            # If less than 4GB available, warn the user
            if available_gb < 4:
                print("WARNING: Less than 4GB GPU memory available")
                print("This may cause issues when loading the model")
                print("Consider using CPU mode by setting LLAMA_CUBLAS=0")
    except Exception as e:
        print(f"Could not check GPU memory: {e}")
    
    # Try with explicit CUDA flag
    os.environ["LLAMA_CUBLAS"] = "1"
    from llama_cpp import Llama
    cuda_available = True
    print("Successfully imported llama_cpp with CUDA enabled")
    
except (ImportError, FileNotFoundError) as e:
    print(f"Error loading llama_cpp with CUDA support: {e}")
    print("Falling back to CPU-only mode. This will be significantly slower.")
    
    # Try alternative approach - disable GPU for llama-cpp
    os.environ["LLAMA_CUBLAS"] = "0"
    try:
        from llama_cpp import Llama
        cuda_available = False
        print("Successfully loaded llama_cpp in CPU-only mode")
    except Exception as inner_e:
        print(f"Failed to import llama_cpp even in CPU mode: {inner_e}")
        raise

class DeepSeekModel:
    def __init__(self, model_path, model_name="deepseek-ai/deepseek-r1-distill-llama-8b", fast_mode=False):
        """
        Initialize a DeepSeek model using llama.cpp GGUF format
        
        Args:
            model_path: Path to the GGUF model file (not used if loading from reference)
            model_name: Original HuggingFace model name (for reference)
            fast_mode: Whether to optimize for speed over quality
        """
        self.model_name = model_name
        self.fast_mode = fast_mode
        
        # Load model reference
        reference_path = os.environ.get("ENGINE_PATH", "../models/model_reference.json")
        if os.path.exists(reference_path):
            try:
                with open(reference_path, "r") as f:
                    reference_data = json.load(f)
                
                # Get GGUF path from reference
                gguf_path = reference_data.get("gguf_path", "")
                if os.path.exists(gguf_path):
                    model_path = gguf_path
                    print(f"Using GGUF model from reference: {gguf_path}")
                    
                    # Update download date if it's the first time
                    if reference_data.get("download_date") is None:
                        reference_data["download_date"] = datetime.now().isoformat()
                        with open(reference_path, "w") as f:
                            json.dump(reference_data, f, indent=2)
            except Exception as e:
                print(f"Error reading model reference: {e}")
        
        # Check if model exists
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"GGUF model file not found. Please run download_gguf.py to download the model.")
        
        # Configure llama.cpp parameters
        if 'cuda_available' in globals() and cuda_available:
            print("CUDA support available - will attempt to use GPU")
            n_gpu_layers = -1  # Use all GPU layers possible
            
            # Add fallback logic in case of CUDA errors
            try:
                # Check if we have enough GPU memory (rough estimate)
                import torch
                if torch.cuda.is_available():
                    free_mem = torch.cuda.mem_get_info()[0] / (1024 ** 3)  # Convert to GB
                    model_size_gb = os.path.getsize(model_path) / (1024 ** 3)
                    
                    print(f"Free GPU memory: {free_mem:.2f} GB")
                    print(f"Model file size: {model_size_gb:.2f} GB")
                    
                    if free_mem < model_size_gb * 1.2:  # Need ~1.2x model size
                        print("WARNING: Not enough GPU memory! Reducing GPU usage...")
                        if free_mem < 2:
                            print("Using CPU only due to limited GPU memory")
                            n_gpu_layers = 0
                        else:
                            # Use partial GPU acceleration
                            n_gpu_layers = 20  # Use fewer layers on GPU
                            print(f"Using limited GPU acceleration: {n_gpu_layers} layers")
            except Exception as e:
                print(f"Error checking GPU memory: {e}")
                # Continue with default settings
        else:
            print("CUDA support not available - using CPU only (slower)")
            n_gpu_layers = 0  # CPU only
            
        n_ctx = 2048  # Context window size
        
        # Apply fast mode optimizations if enabled
        if fast_mode:
            print("⚡ Fast mode enabled: Using faster inference settings")
            n_threads = max(2, os.cpu_count() // 2)  # Half of available cores
            n_batch = 512  # Larger batch size for improved throughput
        else:
            n_threads = max(1, os.cpu_count() - 1)  # Use all but one core
            n_batch = 1024  # Standard batch size
        
        try:
            print(f"Loading GGUF model from {model_path}...")
            self.model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                n_batch=n_batch,
                verbose=True  # Enable verbose mode for better error diagnostics
            )
            print("Model loaded successfully!")
        except RuntimeError as e:
            # Handle CUDA-specific errors
            error_msg = str(e)
            if "CUDA" in error_msg:
                print(f"CUDA error when loading model: {error_msg}")
                print("Attempting to fall back to CPU-only mode...")
                try:
                    self.model = Llama(
                        model_path=model_path,
                        n_ctx=n_ctx,
                        n_gpu_layers=0,  # CPU only
                        n_threads=n_threads,
                        n_batch=n_batch
                    )
                    print("Model loaded successfully in CPU-only mode!")
                except Exception as cpu_e:
                    print(f"Failed to load model even in CPU mode: {cpu_e}")
                    raise
            else:
                print(f"Failed to load model: {e}")
                raise
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise
    
    def _format_prompt(self, text):
        """Format user input into the expected prompt format"""
        # DeepSeek specific prompt formatting
        return f"User: {text}\nAssistant: "
    
    def generate_thoughts(self, prompt):
        """
        Generate 'thoughts' for a given prompt - shows the reasoning process
        """
        try:
            # Create a special prompt to generate thoughts
            thoughts_prompt = f"User: I want you to think step by step about this question and show your reasoning process: {prompt}\nAssistant: Let me think through this step by step:"
            
            # Use lower temperature and different settings for thoughts
            thoughts = self.model(
                thoughts_prompt,
                max_tokens=512,  # Shorter limit for thoughts
                temperature=0.5,  # Lower temperature for more focused thinking
                stop=["User:", "\n\nAssistant:"],
                echo=False
            )
            
            # Extract the generated thoughts
            thoughts_text = thoughts["choices"][0]["text"].strip()
            
            # Format the thoughts nicely
            formatted_thoughts = "Reasoning process:\n\n" + thoughts_text
            
            return formatted_thoughts
        except Exception as e:
            print(f"Error generating thoughts: {e}")
            return "Could not generate thoughts for this response."
    
    def infer(self, prompt, max_tokens=2048, temperature=0.7):
        """Generate a response given a prompt"""
        formatted_prompt = self._format_prompt(prompt)
        
        if self.fast_mode:
            print("⚡ Using fast mode optimizations")
            # Fast mode - use more aggressive settings
            max_new_tokens = min(max_tokens, 1024)  # Limit max output tokens
            response = self.model(
                formatted_prompt,
                max_tokens=max_new_tokens,  # Use fewer tokens
                temperature=temperature,
                stop=["User:"],
                echo=False,
                n_threads=max(6, os.cpu_count()),  # Use more threads
                n_batch=512  # Larger batch size for GPU operations
            )
        else:
            # Standard mode - focus on quality over speed
            response = self.model(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["User:"],
                echo=False
            )
        
        # Extract the generated text
        return response["choices"][0]["text"].strip()
    
    def stream(self, prompt, max_tokens=2048, temperature=0.7):
        """Stream a response token by token"""
        formatted_prompt = self._format_prompt(prompt)
        
        # Apply fast mode optimizations for streaming too
        if self.fast_mode:
            max_tokens = min(max_tokens, 1024)  # Limit max output for faster response
        
        # Initialize streaming
        generated_text = ""
        
        # Use the same parameters for consistency
        for chunk in self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["User:"],
            stream=True,
            echo=False
        ):
            # Get the generated token
            token = chunk["choices"][0]["text"]
            yield token
