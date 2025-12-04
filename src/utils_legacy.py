import os
from datetime import datetime
from pathlib import Path

def group_images_by_session(image_folder: str, threshold_seconds: int = 60) -> list[list[str]]:
    """
    Groups images based on their timestamp.
    Assumes filenames like '20190828_185128.jpg' (YYYYMMDD_HHMMSS)
    """
    path = Path(image_folder)
    files = sorted([f.name for f in path.glob("*.jpg")])
    files.extend(sorted([f.name for f in path.glob("*.JPG")]))
    files.extend(sorted([f.name for f in path.glob("*.jpeg")]))
    files.extend(sorted([f.name for f in path.glob("*.JPEG")]))
    
    # Remove duplicates and sort
    files = sorted(list(set(files)))
        
    groups = []
    current_group = []
    
    for filename in files:
        # Parse time from filename
        try:
            # Handle suffixes like _2, _3
            clean_name = filename.split('.')[0]
            if '_' in clean_name and len(clean_name.split('_')) > 2:
                 parts = clean_name.split('_')
                 clean_name = f"{parts[0]}_{parts[1]}"
            
            current_time = datetime.strptime(clean_name, "%Y%m%d_%H%M%S")
        except (ValueError, IndexError):
            # Try parsing IMG_XXXX format
            # IMG_1495.JPG -> 1495
            try:
                if 'IMG_' in filename:
                    num_part = filename.split('IMG_')[1].split('.')[0]
                    # Create a fake timestamp based on the number to allow delta calculation
                    # 1 unit = 1 second for simplicity, assuming sequential shots are close
                    seq_num = int(num_part)
                    # Use a base time + sequence number
                    current_time = datetime(2000, 1, 1, 0, 0, 0).replace(second=seq_num % 60, minute=(seq_num // 60) % 60)
                    # Store the sequence number as the "time" for delta check
                    # Actually, let's just use a custom object or handle it in the delta check
                    # Simpler: Just map it to a timestamp where 1 unit = 1 second
                    current_time = datetime.fromtimestamp(seq_num) 
                else:
                    raise ValueError("Unknown format")
            except:
                # Handle files that don't match pattern - treat as standalone
                if current_group:
                    groups.append([x['file'] for x in current_group])
                    current_group = []
                groups.append([filename])
                continue

        if not current_group:
            current_group.append({"file": filename, "time": current_time})
            continue
        
        # Calculate delta from the PREVIOUS image in the group
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
