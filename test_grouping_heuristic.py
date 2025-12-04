import os
from datetime import datetime

def group_images_by_session(image_folder, threshold_seconds=60):
    """
    Groups images based on their timestamp.
    Assumes filenames like '20190828_185128.jpg' (YYYYMMDD_HHMMSS)
    """
    files = sorted([f for f in os.listdir(image_folder) if f.endswith(".jpg")])
    groups = []
    current_group = []
    
    for i, filename in enumerate(files):
        # Parse time from filename
        try:
            timestamp_str = filename.split('.')[0] # Adjust regex based on actual filename
            current_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        except ValueError:
            # Handle files that don't match pattern
            continue

        if not current_group:
            current_group.append({"file": filename, "time": current_time})
            continue
        
        # Calculate delta from the first image in the group
        # NOTE: User's code used delta from *first* image, but standard session logic 
        # usually uses delta from *previous* image. 
        # However, for a recipe, "delta from previous" makes sense (scanning page 1, then page 2).
        # Let's stick to "delta from previous" which is what the user's code actually does 
        # (current_group[-1]["time"]).
        
        delta = (current_time - current_group[-1]["time"]).total_seconds()
        
        if delta <= threshold_seconds:
            current_group.append({"file": filename, "time": current_time})
        else:
            # Session gap detected, close group and start new one
            groups.append([x['file'] for x in current_group])
            current_group = [{"file": filename, "time": current_time}]
            
    if current_group:
        groups.append([x['file'] for x in current_group])
        
    return groups

if __name__ == "__main__":
    image_folder = "data/raw/jpg_recipes"
    print(f"Scanning {image_folder}...")
    
    groups = group_images_by_session(image_folder, threshold_seconds=60)
    
    print(f"Found {len(groups)} groups.")
    
    # Print multi-image groups
    print("\n=== MULTI-IMAGE GROUPS ===")
    multi_groups = [g for g in groups if len(g) > 1]
    for g in multi_groups:
        print(g)
        
    print(f"\nTotal multi-image groups: {len(multi_groups)}")
    
    # Check specific known recipes
    print("\n=== VERIFICATION ===")
    
    # Rabbit
    rabbit_files = ["20190828_185219.jpg", "20190828_185223.jpg"]
    rabbit_found = False
    for g in groups:
        if all(f in g for f in rabbit_files):
            print(f"✅ Rabbit recipe grouped correctly: {g}")
            rabbit_found = True
            break
    if not rabbit_found:
        print(f"❌ Rabbit recipe NOT grouped together. Files: {rabbit_files}")

    # Bloody Wong Tong
    bwt_files = ["20190828_185157.jpg", "20190828_185200.jpg"]
    bwt_found = False
    for g in groups:
        if all(f in g for f in bwt_files):
            print(f"✅ Bloody Wong Tong grouped correctly: {g}")
            bwt_found = True
            break
    if not bwt_found:
        print(f"❌ Bloody Wong Tong NOT grouped together. Files: {bwt_files}")
