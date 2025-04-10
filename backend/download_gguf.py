import os
import sys
import argparse
import json
from pathlib import Path
from tqdm import tqdm
from huggingface_hub import HfApi, logging
from huggingface_hub import hf_hub_download, list_repo_files

# Configure minimal logging to avoid excessive output
logging.set_verbosity_error()

def search_huggingface_gguf(model_name):
    """
    Search for GGUF versions of the model on Hugging Face using the Hub API
    """
    # Extract the model name without organization
    if '/' in model_name:
        _, model_short_name = model_name.split('/', 1)
    else:
        model_short_name = model_name
    
    model_short_name = model_short_name.lower()
    
    print(f"Searching for GGUF versions of {model_short_name}...")
    
    api = HfApi()
    results = []
    
    # Search in common repos that might host GGUF models
    common_repos = ["TheBloke", "ggml", "huggingface"]
    
    for repo in common_repos:
        search_query = f"{repo}/{model_short_name}"
        print(f"Checking {search_query}...")
        
        try:
            # Use the API to search models - compatible with older versions
            models = api.list_models(search=search_query)
            
            for model in models:
                if "gguf" in model.id.lower() or "ggml" in model.id.lower():
                    results.append(model.id)
        except Exception as e:
            print(f"Error searching {search_query}: {str(e)}")
    
    # If no results in common repos, do a general search
    if not results:
        try:
            # Search for the model name + gguf
            models = api.list_models(search=f"{model_short_name} gguf")
            
            for model in models:
                if "gguf" in model.id.lower():
                    results.append(model.id)
        except Exception as e:
            print(f"Error performing general search: {str(e)}")
    
    return results

def list_gguf_files(repo_id):
    """
    List GGUF files in a repository using the Hub API
    """
    try:
        # Use the Hub API to list files in the repository
        files = list_repo_files(repo_id)
        
        # Filter for GGUF files
        gguf_files = [file for file in files if file.endswith(".gguf")]
        
        # Sort files by name (simpler than sorting by size since we don't have that info directly)
        gguf_files.sort()
        
        return gguf_files
    except Exception as e:
        print(f"Error listing files in {repo_id}: {str(e)}")
        return []

def download_gguf(repo_id, filename, destination):
    """
    Download a GGUF file from Hugging Face Hub with progress tracking
    """
    try:
        print(f"\nDownloading {filename} from {repo_id}...")
        
        # Use the Hub API to download the file
        # The library handles progress bars internally
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=os.path.dirname(destination),
            local_dir_use_symlinks=False,
            force_download=True
        )
        
        # Rename the file to match the expected destination name
        downloaded_path = os.path.join(os.path.dirname(destination), filename)
        if downloaded_path != destination:
            os.rename(downloaded_path, destination)
            
        return True
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download GGUF models from Hugging Face")
    parser.add_argument("model_name", help="Original model name (e.g., deepseek-ai/deepseek-r1-distill-llama-8b)")
    parser.add_argument("--output-dir", "-o", default="../models", help="Directory to save the model")
    parser.add_argument("--quantization", "-q", default="Q4_K_M", help="Quantization level (e.g. Q4_K_M, Q5_K_M)")
    parser.add_argument("--token", "-t", help="Hugging Face API token for accessing gated models")
    args = parser.parse_args()
    
    # Set API token if provided
    if args.token:
        os.environ["HF_TOKEN"] = args.token
        print("Using provided Hugging Face API token")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Search for GGUF versions
    repos = search_huggingface_gguf(args.model_name)
    
    if not repos:
        print("No GGUF versions found. You may need to convert the model yourself.")
        print("Run python convert_model_simple.py for conversion instructions.")
        return
    
    print(f"Found {len(repos)} potential repositories with GGUF files:")
    for idx, repo in enumerate(repos):
        print(f"[{idx+1}] {repo}")
    
    # Let user select a repository
    repository_tried = []
    while True:
        if repository_tried:
            print("\nRepositories already tried: " + ", ".join(repository_tried))
            
        selection = input("\nSelect a repository number (or press Enter to use the first one, 'list' to show repositories again): ")
        
        if selection.strip().lower() == "list":
            print("\nRepository list:")
            for idx, repo in enumerate(repos):
                print(f"[{idx+1}] {repo}")
            continue
            
        if selection.strip() == "":
            repo_idx = 0
        else:
            try:
                repo_idx = int(selection) - 1
                if repo_idx < 0 or repo_idx >= len(repos):
                    print(f"Invalid selection {selection}. Using the first repository.")
                    repo_idx = 0
            except ValueError:
                print(f"Invalid input '{selection}'. Using the first repository.")
                repo_idx = 0
        
        selected_repo = repos[repo_idx]
        if selected_repo in repository_tried:
            print(f"You already tried {selected_repo}. Trying anyway...")
        
        print(f"\nUsing repository: {selected_repo}")
        repository_tried.append(selected_repo)
        
        # List GGUF files
        gguf_files = list_gguf_files(selected_repo)
        
        if not gguf_files:
            print(f"No GGUF files found in {selected_repo}")
            retry = input("Would you like to try another repository? (y/n): ")
            if retry.lower() == 'y':
                continue
            else:
                print("You can download GGUF models manually and place them in the models directory.")
                return
        
        # Found GGUF files
        print(f"\nFound {len(gguf_files)} GGUF files:")
        quant_preference = args.quantization.lower()
        best_match = None
        
        for idx, file in enumerate(gguf_files):
            # Mark files that match the requested quantization
            if quant_preference in file.lower():
                print(f"[{idx+1}] {file} ✓")
                if best_match is None:
                    best_match = idx
            else:
                print(f"[{idx+1}] {file}")
        
        # Break the loop as we found valid files
        break
    
    # Let user select a file
    selection = input("\nSelect a file number (or press Enter for recommended): ")
    if selection.strip() == "":
        if best_match is not None:
            file_idx = best_match
        else:
            file_idx = 0
    else:
        try:
            file_idx = int(selection) - 1
            if file_idx < 0 or file_idx >= len(gguf_files):
                print("Invalid selection. Using the first file.")
                file_idx = 0
        except ValueError:
            print("Invalid selection. Using the first file.")
            file_idx = 0
    
    selected_file = gguf_files[file_idx]
    print(f"\nSelected: {selected_file}")
    
    # Download the file
    output_path = os.path.join(args.output_dir, os.path.basename(selected_file))
    
    success = download_gguf(selected_repo, selected_file, output_path)
    
    if success:
        print(f"\nSuccessfully downloaded to {output_path}")
        
        # Update the model reference
        model_short_name = args.model_name.split('/')[-1].lower()
        reference_file = os.path.join(args.output_dir, "model_reference.json")
        reference_data = {
            "model_name": args.model_name,
            "type": "gguf",
            "gguf_path": output_path,
            "quantization": args.quantization,
            "download_date": None  # Will be set when model is first loaded
        }
        
        with open(reference_file, "w") as f:
            json.dump(reference_data, f, indent=2)
            
        print(f"Model reference updated in {reference_file}")
        print("\nYou can now run the application with the downloaded model")
    else:
        print("\nFailed to download the model. Please try again or select a different file.")

if __name__ == "__main__":
    main()
