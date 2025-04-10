import os
import sys

def check_gpu_memory():
    """
    Check if there is enough GPU memory available to load the model
    Returns: (has_gpu, available_gb, is_sufficient)
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return False, 0, False
        
        # Get device details
        device = torch.cuda.current_device()
        device_name = torch.cuda.get_device_name(device)
        total_memory = torch.cuda.get_device_properties(device).total_memory
        free_memory, total = torch.cuda.mem_get_info(device)
        
        # Convert to GB
        total_gb = total_memory / (1024**3)
        free_gb = free_memory / (1024**3)
        
        print(f"GPU: {device_name}")
        print(f"Total GPU memory: {total_gb:.2f} GB")
        print(f"Free GPU memory: {free_gb:.2f} GB")
        
        # Check if enough memory is available (need ~2GB for 8B parameter model)
        is_sufficient = free_gb >= 2.0
        
        if not is_sufficient:
            print(f"WARNING: Only {free_gb:.2f} GB free GPU memory available")
            print("The model may fail to load with CUDA acceleration.")
        
        return True, free_gb, is_sufficient
    except Exception as e:
        print(f"Error checking GPU memory: {e}")
        return False, 0, False

if __name__ == "__main__":
    has_gpu, available_gb, is_sufficient = check_gpu_memory()
    
    if not has_gpu:
        print("No GPU detected. Model will run in CPU-only mode (slower).")
        sys.exit(1)
    
    if not is_sufficient:
        print("Insufficient GPU memory. Consider:")
        print("1. Close other applications to free up GPU memory")
        print("2. Use a smaller model")
        print("3. Force CPU mode by setting LLAMA_CUBLAS=0 environment variable")
        sys.exit(2)
    
    print(f"GPU check passed: {available_gb:.2f} GB available")
    sys.exit(0)
