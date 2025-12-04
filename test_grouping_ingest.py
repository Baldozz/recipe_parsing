from src.ingest import ingest_images
import shutil
import os

def run_test():
    input_dir = "data/raw/test_complex_email"
    output_dir = "data/parsed_test_grouping"
    
    # Clean output dir
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    print(f"Running ingestion on {input_dir}...")
    ingest_images(input_dir, output_dir, skip_duplicates=False)
    
    print("\nChecking results...")
    for f in os.listdir(output_dir):
        if f.endswith(".json") and not f.startswith("_"):
            print(f"Generated: {f}")

if __name__ == "__main__":
    run_test()
