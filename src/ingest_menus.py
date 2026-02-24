import os
import json
import time
from pathlib import Path
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def parse_menu(text, filename):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
    You are an expert culinary assistant. Extract the structured details of the following restaurant or private chef menu.
    Output ONLY a valid JSON object with no markdown formatting around it.
    
    The JSON structure MUST be:
    {{
      "filename": "{filename}",
      "event_date": "YYYY-MM-DD or unknown",
      "event_name": "Name of the event or 'Private Dinner' if unknown",
      "courses": [
        {{
          "course_name": "e.g., Starters, Main Course, Dessert, or Course 1",
          "dishes": [
            {{
              "dish_name": "Name of the dish",
              "description": "Any additional ingredients or details listed under the dish"
            }}
          ]
        }}
      ]
    }}
    
    MENU TEXT:
    {text}
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            # Clean up the response to just getting the JSON
            res_text = response.text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            
            parsed_data = json.loads(res_text.strip())
            return parsed_data
        except Exception as e:
            if "Resource exhausted" in str(e) or "429" in str(e):
                print(f"Rate limited. Retrying in {5 * (attempt + 1)}s...")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"Error parsing menu with Gemini at {filename}: {e}")
                return None
    return None

def main():
    source_dir = Path("../../ALL MENU")
    output_dir = Path("data/parsed_menus")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not source_dir.exists():
         print(f"Source directory not found: {source_dir.resolve()}")
         return
         
    pdf_files = list(source_dir.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF menus to parse.")
    
    success_count = 0
    
    for p in pdf_files:
        out_file = output_dir / f"{p.stem}.json"
        if out_file.exists():
            continue # Skip if already parsed
            
        print(f"Processing: {p.name}...")
        text = extract_text(p)
        if not text:
            continue
            
        parsed = parse_menu(text, p.name)
        if parsed:
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            success_count += 1
            
        # Add a tiny sleep to respect rate limits if doing sequentially
        time.sleep(1)
        
    print(f"\n🎉 Successfully parsed and saved {success_count} menus to {output_dir}")

if __name__ == "__main__":
    main()
