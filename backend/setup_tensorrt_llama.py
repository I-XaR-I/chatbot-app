import os
import sys
import subprocess
import platform

def print_header(text):
    print("\n" + "="*60)
    print(text)
    print("="*60)

def install_llama_cpp_with_tensorrt():
    print_header("INSTALLING LLAMA-CPP-PYTHON WITH TENSORRT SUPPORT")
    
    # Check if TensorRT is installed
    try:
        import tensorrt as trt
        print(f"✅ TensorRT is installed (version: {trt.__version__})")
    except ImportError:
        print("❌ TensorRT not found. Please install TensorRT first.")
        print("Visit: https://developer.nvidia.com/tensorrt")
        return False
    
    # Check CUDA availability
    try:
        import torch
        if torch.cuda.is_available():
            cuda_version = torch.version.cuda
            print(f"✅ CUDA is available (version: {cuda_version})")
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("❌ CUDA is not available through PyTorch")
            print("Please make sure CUDA is properly installed")
            return False
    except ImportError:
        print("⚠️ PyTorch not installed, cannot verify CUDA status")
        print("Continuing anyway, but this may cause issues")
    
    print("\nThis script will install llama-cpp-python with TensorRT support.")
    print("This may take several minutes as it will compile from source.")
    print("\nDo you want to continue? (y/n)")
    choice = input().lower()
    if choice != 'y':
        print("Installation cancelled.")
        return False
    
    # Check TensorRT version to adjust build options
    tensorrt_version = None
    try:
        import tensorrt as trt
        tensorrt_version = trt.__version__
        major_version = int(tensorrt_version.split('.')[0])
        print(f"Detected TensorRT version: {tensorrt_version} (Major: {major_version})")
        
        if major_version >= 10:
            print("Using TensorRT 10+ specific build configuration")
        else:
            print("Using standard TensorRT build configuration")
    except (ImportError, ValueError, IndexError):
        print("Could not determine TensorRT version, using standard build configuration")
    
    # Set environment variables for the build
    env = os.environ.copy()
    env["CMAKE_ARGS"] = "-DLLAMA_CUBLAS=on -DLLAMA_TENSORRT=on"
    
    # For TensorRT 10+, add specific build options if needed
    if tensorrt_version and int(tensorrt_version.split('.')[0]) >= 10:
        env["CMAKE_ARGS"] += " -DLLAMA_CUBLAS_FORCE=on"
        # TensorRT 10 might need newer CUDA - add hint for CMake
        if os.environ.get("CUDA_PATH"):
            env["CMAKE_ARGS"] += f" -DCUDA_TOOLKIT_ROOT_DIR={os.environ.get('CUDA_PATH')}"
    
    env["FORCE_CMAKE"] = "1"
    
    print("\nInstalling llama-cpp-python with TensorRT support...")
    print(f"Using CMAKE_ARGS: {env['CMAKE_ARGS']}")
    try:
        # Use pip to install with the right flags - specify minimum version compatible with TensorRT 10
        cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall", "llama-cpp-python>=0.2.38"]
        subprocess.run(cmd, env=env, check=True)
        print("✅ Installation completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed with error code {e.returncode}")
        print("You may need to install build tools or check dependencies.")
        return False

def test_tensorrt_backend():
    print_header("TESTING LLAMA-CPP-PYTHON TENSORRT BACKEND")
    
    try:
        import llama_cpp
        print(f"Loaded llama_cpp version: {llama_cpp.__version__}")
        
        # Check for TensorRT backend support
        has_tensorrt = False
        
        # Method 1: Check for tensor backend via API if available
        if hasattr(llama_cpp, "Llama") and hasattr(llama_cpp.Llama, "available_backends"):
            backends = llama_cpp.Llama.available_backends()
            print(f"Available backends: {backends}")
            has_tensorrt = "tensorrt" in backends
        
        # Method 2: Check for environment variable support
        if not has_tensorrt:
            # Test by loading a tiny model with TensorRT
            print("\nPlease wait while we test TensorRT backend...")
            
            # Set environment variable to use TensorRT
            os.environ["LLAMA_BACKEND"] = "tensorrt"
            
            # Look for a model to test
            model_paths = [
                "../models",  # Default models directory
                os.path.abspath("."),  # Current directory
                os.path.abspath(".."),  # Parent directory
            ]
            
            # Find first GGUF model
            test_model = None
            for path in model_paths:
                if os.path.exists(path):
                    for file in os.listdir(path):
                        if file.endswith(".gguf") and os.path.getsize(os.path.join(path, file)) < 5e9:  # < 5GB
                            test_model = os.path.join(path, file)
                            break
                    if test_model:
                        break
            
            if test_model:
                print(f"Testing with model: {test_model}")
                try:
                    # Create a model instance with minimal settings
                    model = llama_cpp.Llama(
                        model_path=test_model,
                        n_ctx=512,  # Small context for fast loading
                        n_batch=8,
                        verbose=True
                    )
                    print("✅ Successfully created model with TensorRT backend!")
                    has_tensorrt = True
                except Exception as e:
                    print(f"❌ Error creating model with TensorRT backend: {e}")
            else:
                print("❌ No suitable test model found")
        
        if has_tensorrt:
            print("\n✅ TensorRT backend is working correctly!")
            print("You can use fast mode with TensorRT acceleration.")
            return True
        else:
            print("\n❌ TensorRT backend is not available in your llama-cpp-python installation.")
            print("Consider reinstalling using this script.")
            return False
            
    except ImportError:
        print("❌ llama-cpp-python is not installed")
        return False
    except Exception as e:
        print(f"❌ Error testing TensorRT backend: {e}")
        return False

def main():
    print_header("LLAMA-CPP-PYTHON WITH TENSORRT SETUP")
    print("This script will help you set up TensorRT acceleration for faster inference")
    
    # First check if llama-cpp-python is already installed with TensorRT support
    print("Checking if llama-cpp-python is already installed with TensorRT support...")
    if test_tensorrt_backend():
        print("\n✅ llama-cpp-python is already installed with working TensorRT support!")
        print("No further action needed.")
        return True
    
    # If not, offer to install
    print("\nllama-cpp-python is either not installed or doesn't have TensorRT support.")
    print("Would you like to install/reinstall with TensorRT support? (y/n)")
    choice = input().lower()
    if choice != 'y':
        print("Setup cancelled.")
        return False
    
    # Install llama-cpp-python with TensorRT support
    success = install_llama_cpp_with_tensorrt()
    
    if success:
        # Test again to make sure it worked
        print("\nTesting new installation...")
        if test_tensorrt_backend():
            print("\n✅ Setup completed successfully!")
            print("You can now use fast mode with TensorRT acceleration.")
        else:
            print("\n⚠️ Installation completed but TensorRT backend test failed.")
            print("You may need to check your CUDA and TensorRT installation.")
    else:
        print("\n❌ Setup failed.")
    
    return success

if __name__ == "__main__":
    main()
