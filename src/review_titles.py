import json
import os
from pathlib import Path
from src.config import get_chat_client, CHAT_MODEL

def check_title_typo(name, ingredients):
    """Uses LLM to check if a title is likely a typo given the ingredients."""
    client = get_chat_client()
    
    prompt = f"""Analyze this recipe title and ingredients.
    
Title: "{name}"
Ingredients: {', '.join(ingredients[:10])}...

Is the title likely a misspelling of a known culinary dish?
Example: "Oricneni" -> "Orecchiette" (Likely Typo)
Example: "Beef Stew" -> "Beef Stew" (Correct)
Example: "Xkjhsd" -> (Unknown/Typo)

Return JSON:
{{
  "is_suspicious": boolean,
  "suggested_correction": string (or null if correct),
  "reason": string
}}
"""
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a culinary expert and spell checker. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error checking title '{name}': {e}")
        return {"is_suspicious": False, "suggested_correction": None, "reason": "Error"}

def review_titles(data_dir="data/parsed"):
    path = Path(data_dir)
    files = list(path.glob("*.json"))
    
    print(f"Scanning {len(files)} recipes for typos...")
    
    suspicious_count = 0
    
    for p in files:
        try:
            with open(p, "r") as f:
                data = json.load(f)
            
            name = data.get("name", "")
            ingredients = data.get("ingredients", [])
            
            # Skip empty names or obviously generic ones if needed
            if not name: 
                continue

            # Check with LLM
            result = check_title_typo(name, ingredients)
            
            if result.get("is_suspicious"):
                suspicious_count += 1
                print(f"\n[SUSPICIOUS] File: {p.name}")
                print(f"  Current Title: '{name}'")
                print(f"  Suggestion:    '{result.get('suggested_correction')}'")
                print(f"  Reason:        {result.get('reason')}")
                
                # Interactive Loop
                choice = input("  Action? (y=Accept Suggestion, k=Keep Current, e=Edit Manually): ").strip().lower()
                
                new_name = name
                if choice == 'y' and result.get('suggested_correction'):
                    new_name = result['suggested_correction']
                elif choice == 'e':
                    new_name = input("  Enter correct title: ").strip()
                
                if new_name != name:
                    data["name"] = new_name
                    with open(p, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"  Updated to: '{new_name}'")
                else:
                    print("  Kept original.")

        except Exception as e:
            print(f"Error processing {p}: {e}")

    print(f"\nReview Complete. Found {suspicious_count} suspicious titles.")

if __name__ == "__main__":
    review_titles()
