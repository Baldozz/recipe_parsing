"""Test the integrated three-phase pipeline with a small dataset."""

import subprocess
import shutil
from pathlib import Path


def setup_small_test():
    """Create small test dataset."""
    test_dir = Path("data/raw/test_small")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy first 10 images
    jpg_dir = Path("data/raw/jpg_recipes")
    images = sorted(jpg_dir.glob("*.jpg"))[:10]
    
    for img in images:
        shutil.copy(img, test_dir / img.name)
    
    print(f"Copied {len(images)} images to test directory")
    return len(images)


def run_test_pipeline():
    """Run pipeline on test data."""
    # Temporarily replace jpg_recipes with test_small
    jpg_dir = Path("data/raw/jpg_recipes")
    backup_dir = Path("data/raw/jpg_recipes_backup")
    test_dir = Path("data/raw/test_small")
    
    # Backup original
    if jpg_dir.exists():
        shutil.move(str(jpg_dir), str(backup_dir))
    
    # Use test data
    shutil.move(str(test_dir), str(jpg_dir))
    
    try:
        # Run pipeline
        print("\n" + "=" * 60)
        print("RUNNING THREE-PHASE PIPELINE")
        print("=" * 60)
        
        result = subprocess.run(
            ["bash", "run_pipeline.sh"],
            cwd="/Users/fabiobaldini/Desktop/Projects/Ludo_Project/RAG_RECIPES/recipe_parsing",
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    finally:
        # Restore original
        shutil.move(str(jpg_dir), str(test_dir))
        shutil.move(str(backup_dir), str(jpg_dir))


def verify_results():
    """Check results from all three phases."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Check Phase 1 output
    parsed = list(Path("data/parsed").glob("*.json"))
    print(f"\nPhase 1 (Parsed): {len(parsed)} recipes")
    
    # Check Phase 2 output
    stitched = list(Path("data/stitched").glob("*.json"))
    print(f"Phase 2 (Stitched): {len(stitched)} recipes")
    
    # Check Phase 3 output
    linked = list(Path("data/linked").glob("*.json"))
    print(f"Phase 3 (Linked): {len(linked)} recipes")
    
    if linked:
        # Check for recipes with links
        import json
        linked_count = 0
        for file in linked:
            with open(file) as f:
                recipe = json.load(f)
            if 'requires' in recipe or 'used_in' in recipe:
                linked_count += 1
                print(f"\n{recipe['name']}:")
                if 'requires' in recipe:
                    print(f"  Requires: {recipe['requires']}")
                if 'used_in' in recipe:
                    print(f"  Used in: {recipe['used_in']}")
        
        print(f"\n{linked_count}/{len(linked)} recipes have component relationships")


if __name__ == "__main__":
    # setup_small_test()
    # success = run_test_pipeline()
    # 
    # if success:
    #     verify_results()
    # else:
    #     print("Pipeline failed!")
    
    # For now, just verify existing results
    verify_results()
