import os
import json
import subprocess
import sys
import platform

def convert_model_simple(model_name="deepseek-ai/deepseek-r1-distill-llama-8b", 
                         output_dir="../models/",
                         quantize="Q4_K_M"):
    """
    Create a model reference file for GGUF format and provide conversion instructions
    """
    print(f"Setting up reference for {model_name}...")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse model name
    model_short_name = model_name.split('/')[-1].lower()
    
    # Expected GGUF file paths
    gguf_filename = f"{model_short_name}-{quantize}.gguf"
    gguf_path = os.path.join(output_dir, gguf_filename)
    
    # Save model reference information
    reference_file = os.path.join(output_dir, "model_reference.json")
    reference_data = {
        "model_name": model_name,
        "type": "gguf",
        "gguf_path": gguf_path,
        "quantization": quantize,
        "download_date": None  # Will be set when model is first loaded
    }
    
    with open(reference_file, "w") as f:
        json.dump(reference_data, f, indent=2)
    
    print(f"Model reference saved to {reference_file}")
    
    # Check if GGUF file already exists
    if os.path.exists(gguf_path):
        print(f"GGUF model file already exists at {gguf_path}")
        return True
    
    # Generate conversion instructions
    print("\n" + "="*60)
    print("GGUF MODEL FILE NOT FOUND")
    print("="*60)
    print(f"The GGUF model file was not found at: {gguf_path}")
    print("\nTo convert or download a GGUF model, you can:")
    
    print("\n1. Download pre-converted GGUF models from Hugging Face:")
    print(f"   Look for '{model_short_name}' GGUF files on https://huggingface.co/models")
    
    print("\n2. Convert the model yourself using llama.cpp:")
    print(f"   a) Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp.git")
    print(f"   b) Build llama.cpp")
    print(f"   c) Convert: python llama.cpp/convert.py {model_name} --outfile {gguf_path}")
    print(f"      To quantize: python llama.cpp/quantize.py {gguf_path} {gguf_path} {quantize}")
    
    print("\nOnce you have the GGUF file, place it at:")
    print(f"  {gguf_path}")
    print("Then restart the application")
    
    # Create a conversion batch script for Windows
    if platform.system() == "Windows":
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "convert_to_gguf.bat")
        with open(bat_path, "w") as f:
            f.write("@echo off\n")
            f.write("echo Converting model to GGUF format...\n")
            f.write("echo This may take a while and requires git and Python\n\n")
            f.write("if not exist llama.cpp (\n")
            f.write("  echo Cloning llama.cpp repository...\n")
            f.write("  git clone https://github.com/ggerganov/llama.cpp.git\n")
            f.write("  cd llama.cpp\n")
            f.write("  echo Building llama.cpp...\n")
            f.write("  cmake -B build\n")
            f.write("  cmake --build build --config Release\n")
            f.write("  cd ..\n")
            f.write(")\n\n")
            f.write(f"echo Converting {model_name} to GGUF...\n")
            f.write(f"python llama.cpp/convert.py {model_name} --outfile {gguf_path}.tmp\n")
            f.write(f"echo Quantizing to {quantize}...\n")
            f.write(f"python llama.cpp/quantize.py {gguf_path}.tmp {gguf_path} {quantize}\n")
            f.write(f"del {gguf_path}.tmp\n")
            f.write("echo Done! You can now use the model with the application\n")
            f.write("pause\n")
        
        print(f"\nA conversion script has been created at {bat_path}")
        print("You can run this script to automatically convert the model")
    
    return False

if __name__ == "__main__":
    convert_model_simple()
