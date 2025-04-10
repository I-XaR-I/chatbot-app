import os
import sys
import subprocess
import platform

def print_header(text):
    print("\n" + "="*50)
    print(text)
    print("="*50)

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def check_nvidia_driver():
    print_header("CHECKING NVIDIA DRIVER")
    if platform.system() == "Windows":
        output = run_command("nvidia-smi")
        if "NVIDIA-SMI" in output:
            print("✅ NVIDIA driver is installed and functioning")
            print("\n".join(output.split('\n')[0:6]))
            return True
        else:
            print("❌ NVIDIA driver not detected or not working properly")
            print("Please install or update your NVIDIA drivers from: https://www.nvidia.com/Download/index.aspx")
            return False
    else:
        print("Non-Windows system detected, skipping Windows-specific checks")
        return None

def check_pytorch():
    print_header("CHECKING PYTORCH INSTALLATION")
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        
        if "+cu" in torch.__version__:
            print("✅ PyTorch with CUDA support is installed")
        else:
            print("❌ You have the CPU-only version of PyTorch")
            print("You need to reinstall PyTorch with CUDA support")
        
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU device: {torch.cuda.get_device_name(0)}")
            print(f"GPU count: {torch.cuda.device_count()}")
            print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            return True
        else:
            print("❌ CUDA is not available to PyTorch")
            return False
    except ImportError:
        print("❌ PyTorch is not installed")
        return False

def check_llama_cpp():
    print_header("CHECKING LLAMA.CPP COMPATIBILITY")
    try:
        import llama_cpp
        print(f"✅ llama-cpp-python is installed (version: {llama_cpp.__version__})")
        
        # Check if built with CUDA support
        cuda_available = hasattr(llama_cpp, "_lib") and hasattr(llama_cpp._lib, "llama_backend_cuda")
        if cuda_available:
            print("✅ llama-cpp-python is built with CUDA support")
        else:
            print("❌ llama-cpp-python is NOT built with CUDA support")
            print("Consider reinstalling with: pip install llama-cpp-python[cuda]")
            
        return True
    except ImportError:
        print("❌ llama-cpp-python is not installed")
        print("Install with: pip install llama-cpp-python[cuda]")
        return False

def check_cuda_toolkit():
    print_header("CHECKING CUDA TOOLKIT")
    # Check NVCC version
    nvcc_output = run_command("nvcc --version")
    if "release" in nvcc_output.lower():
        print("✅ CUDA Toolkit is installed")
        print(nvcc_output.strip().split("\n")[3])
        return True
    else:
        print("❌ CUDA Toolkit not detected in PATH")
        print("This might not be an issue if PyTorch comes with its own CUDA libraries")
        return False

def check_gguf_models():
    print_header("CHECKING FOR GGUF MODELS")
    # Common locations to check for GGUF models
    locations = [
        os.path.join(os.getcwd(), "models"),
        os.path.join(os.getcwd(), "..", "models"),
        os.path.join(os.getcwd())
    ]
    
    found_models = []
    
    for location in locations:
        if os.path.exists(location):
            for file in os.listdir(location):
                if file.endswith(".gguf"):
                    found_models.append(os.path.join(location, file))
    
    if found_models:
        print(f"✅ Found {len(found_models)} GGUF model(s):")
        for model in found_models[:5]:  # Show first 5 models
            print(f"  - {os.path.basename(model)}")
        if len(found_models) > 5:
            print(f"  - ... and {len(found_models) - 5} more")
        return True
    else:
        print("❌ No GGUF models found in common locations")
        print("You need to download or convert models to GGUF format.")
        print("Run convert_model_simple.py to get detailed instructions.")
        return False

def check_cuda_path():
    print_header("CHECKING CUDA PATH")
    
    cuda_path = os.environ.get("CUDA_PATH", None)
    if cuda_path:
        print(f"CUDA_PATH is set to: {cuda_path}")
        
        if os.path.exists(cuda_path):
            print("✅ CUDA path exists")
            
            cuda_bin = os.path.join(cuda_path, "bin")
            if os.path.exists(cuda_bin):
                print(f"✅ CUDA bin directory exists: {cuda_bin}")
                
                # Check for crucial CUDA files
                if platform.system() == "Windows":
                    crucial_files = ["cublas64_*.dll", "cudart64_*.dll"]
                    found_all = True
                    
                    for pattern in crucial_files:
                        import glob
                        files = glob.glob(os.path.join(cuda_bin, pattern))
                        if files:
                            print(f"✅ Found {os.path.basename(files[0])}")
                        else:
                            print(f"❌ Could not find any file matching {pattern}")
                            found_all = False
                    
                    return found_all
            else:
                print(f"❌ CUDA bin directory not found at {cuda_bin}")
                return False
        else:
            print(f"❌ CUDA_PATH points to non-existent directory: {cuda_path}")
            return False
    else:
        print("❌ CUDA_PATH environment variable is not set")
        
        # Check common locations for CUDA v12.8
        common_cuda_paths = [
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0",
        ]
        
        for path in common_cuda_paths:
            if os.path.exists(path):
                print(f"✅ Found CUDA installation at {path}, but CUDA_PATH is not set")
                print(f"   Run fix_dependencies.py to set CUDA_PATH correctly")
                return False
        
        return False

def main():
    print_header("GPU DETECTION AND TROUBLESHOOTING TOOL")
    
    # Check NVIDIA driver first
    driver_ok = check_nvidia_driver()
    if driver_ok is False:
        print("\nYou need to install NVIDIA drivers before continuing")
        print("Download the appropriate driver from: https://www.nvidia.com/Download/index.aspx")
        return
    
    # Check CUDA PATH (new)
    cuda_path_ok = check_cuda_path()
    if not cuda_path_ok:
        print("\nCUDA_PATH is not properly set or points to an invalid location.")
        print("This will prevent GPU acceleration for llama-cpp-python.")
        print("Run the fix_dependencies.py script and use the 'Fix CUDA_PATH environment variable' option.")
    
    # Check CUDA toolkit (optional)
    cuda_toolkit_ok = check_cuda_toolkit()
    
    # Check PyTorch
    pytorch_ok = check_pytorch()
    
    # Check llama.cpp compatibility
    llama_cpp_ok = check_llama_cpp()
    
    # Check for GGUF models
    gguf_models_ok = check_gguf_models()
    
    if not pytorch_ok:
        print("\nWould you like to fix PyTorch installation now? (y/n)")
        choice = input().lower()
        if choice == 'y':
            print("\nPlease run the fix_pytorch_cuda.bat script in this directory")
            print("Or run this command manually:")
            print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        else:
            print("\nTo fix PyTorch manually, run:")
            print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    
    if not llama_cpp_ok:
        print("\nWould you like to install llama-cpp-python with CUDA support now? (y/n)")
        choice = input().lower()
        if choice == 'y':
            print("\nInstalling llama-cpp-python with CUDA support...")
            subprocess.run("pip install llama-cpp-python[cuda]", shell=True)
        else:
            print("\nTo install llama-cpp-python manually, run:")
            print("pip install llama-cpp-python[cuda]")
    
    if not gguf_models_ok:
        print("\nYou need to download or convert models to GGUF format")
        print("Run python convert_model_simple.py for instructions")
    
    if pytorch_ok and llama_cpp_ok and (gguf_models_ok or driver_ok):
        print("\n✅ Your GPU setup appears to be working correctly!")
        print("You can now run your chatbot application with GPU acceleration.")
    else:
        print("\n⚠️ Some components are missing or not configured correctly.")
        print("Please address the issues mentioned above.")

if __name__ == "__main__":
    main()
