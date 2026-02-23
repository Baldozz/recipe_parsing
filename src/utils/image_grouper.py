from pathlib import Path
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

class ImageGrouper:
    """
    Groups images into 'documents' based on timestamps and filename patterns.
    """
    
    
    def __init__(self, time_gap_threshold_seconds: int = 60, max_group_size: int = 8):
        self.time_gap_threshold = timedelta(seconds=time_gap_threshold_seconds)
        self.max_group_size = max_group_size
        # Regex for YYYYMMDD_HHMMSS format (e.g., 20190828_185157.jpg)
        self.timestamp_pattern = re.compile(r"(\d{8})_(\d{6})")

    def _extract_timestamp(self, filename: str) -> datetime | None:
        """Extract datetime from filename if it matches the pattern."""
        match = self.timestamp_pattern.search(filename)
        if match:
            date_str, time_str = match.groups()
            try:
                return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except ValueError:
                return None
        return None

    def _extract_sequence(self, filename: str) -> int | None:
        """Extract a sequence number from filenames like 'IMG_1234.jpg' or '...WA0004.jpg'."""
        # Look for the last sequence of digits before the extension
        match = re.search(r"(\d+)[^\d]*$", Path(filename).stem)
        if match:
            return int(match.group(1))
        return None

    def group_images(self, image_paths: List[Path]) -> List[List[Path]]:
        """
        Groups a list of image paths into clusters.
        
        Logic:
        1. Sort by filename.
        2. Iterate through sorted images.
        3. Group if:
           a) Timestamps are within threshold.
           b) OR: Filenames look like a sequence (e.g. WA0001, WA0002) and are adjacent.
        """
        if not image_paths:
            return []

        # Sort primarily by alphanumeric filename
        sorted_paths = sorted(image_paths, key=lambda p: p.name)
        
        groups: List[List[Path]] = []
        current_group: List[Path] = []
        
        # Trackers for the current group
        last_timestamp: datetime | None = None
        last_sequence: int | None = None
        last_stem_prefix: str | None = None # To ensure we don't group "A_1.jpg" with "B_2.jpg"
        
        for img_path in sorted_paths:
            current_timestamp = self._extract_timestamp(img_path.name)
            current_sequence = self._extract_sequence(img_path.name)
            
            # Determine prefix (everything before the sequence number) to ensure we only group same-series files
            current_stem_prefix = None
            if current_sequence is not None:
                match = re.search(r"^(.*)\d+[^\d]*$", Path(img_path.name).stem)
                if match:
                    current_stem_prefix = match.group(1)

            if not current_group:
                # Start first group
                current_group.append(img_path)
                last_timestamp = current_timestamp
                last_sequence = current_sequence
                last_stem_prefix = current_stem_prefix
                continue
            
            should_group = False
            
            # 1. Check Timestamp
            if last_timestamp and current_timestamp:
                time_diff = current_timestamp - last_timestamp
                if abs(time_diff) <= self.time_gap_threshold:
                    should_group = True
            
            # 2. Check Sequence (only if timestamps didn't match or weren't present)
            if not should_group and last_sequence is not None and current_sequence is not None:
                # Check if prefixes match (e.g. "IMG-2017-" vs "IMG-2017-")
                if last_stem_prefix == current_stem_prefix:
                    # Check if sequence is close (allow gaps of up to 2, e.g. missing page)
                    if 0 < (current_sequence - last_sequence) <= 2:
                        should_group = True

            if should_group:
                # Check Size Limit
                if len(current_group) >= self.max_group_size:
                     # Force split
                     should_group = False
                else:
                    current_group.append(img_path)
                    # Update trackers
                    if current_timestamp: last_timestamp = current_timestamp
                    if current_sequence is not None: last_sequence = current_sequence
                    # prefix stays same
            
            if not should_group:
                # Close current group and start new one
                groups.append(current_group)
                current_group = [img_path]
                last_timestamp = current_timestamp
                last_sequence = current_sequence
                last_stem_prefix = current_stem_prefix
        
        # Append the final group
        if current_group:
            groups.append(current_group)
            
        return groups

    def print_grouping_summary(self, groups: List[List[Path]]):
        """Helper to print summary of groups found."""
        print(f"Found {len(groups)} groups from total images.")
        for i, group in enumerate(groups, 1):
            if len(group) > 1:
                print(f"  Group {i}: {len(group)} images")
                for img in group:
                    print(f"    - {img.name}")
            # Single images are skipped in summary to avoid noise, or can be printed if verbose
