import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.utils.json_utils import extract_json_from_text

from dotenv import load_dotenv
load_dotenv()

# Configuration
INPUT_DIR = Path("data/merged_llm")
OUTPUT_DIR = Path("data/english_dataset")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def translate_recipe(data: dict) -> dict:
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    You are a professional culinary translator.
    translate the following recipe content into clear, standard English.
    Keep the structure identical (ingredients list, steps list).
    Do NOT translate brand names or specific proper nouns if they are chemically significant, but DO translate ingredient names (e.g. "Farina" -> "Flour").
    
    INPUT:
    Name: {data.get('name')}
    Ingredients: {json.dumps(data.get('ingredients', []))}
    Steps: {json.dumps(data.get('steps', []))}
    
    OUTPUT JSON:
    {{
      "name": "English Name",
      "ingredients": ["ing1", "ing2"],
      "steps": ["step1", "step2"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = extract_json_from_text(response.text)
        translated = json.loads(text)
        
        # Update data
        data['name'] = translated.get('name', data['name'])
        data['ingredients'] = translated.get('ingredients', data['ingredients'])
        data['steps'] = translated.get('steps', data['steps'])
        
        # Update metadata
        other = data.get('other_details', {})
        other['original_language'] = data.get('language')
        other['translated_from'] = data.get('language')
        data['other_details'] = other
        data['language'] = 'en'
        
        return data
    except Exception as e:
        print(f"Translation Error for {data.get('name')}: {e}")
        return None

def process_file(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Check top level or other_details
        lang = data.get('language')
        if not lang:
            lang = data.get('other_details', {}).get('language', 'en')
            
        lang = lang.lower()
        
        # Define output path
        rel_path = file_path.relative_to(INPUT_DIR)
        out_path = OUTPUT_DIR / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        if lang == 'en':
            # Just copy
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return "Copied"
            
        else:
            # Translate
            translated_data = translate_recipe(data)
            if translated_data:
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(translated_data, f, indent=2, ensure_ascii=False)
                return f"Translated ({lang} -> en)"
            else:
                return f"Failed to Translate ({file_path.name})"
                
    except Exception as e:
        return f"Error {file_path.name}: {e}"

def main():
    print(f"Standardizing Dataset to English...")
    print(f"Source: {INPUT_DIR}")
    print(f"Target: {OUTPUT_DIR}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    files = list(INPUT_DIR.rglob("*.json"))
    print(f"Found {len(files)} files.")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_file, f): f for f in files}
        
        stats = {"Copied": 0, "Translated": 0, "Failed": 0}
        
        for future in tqdm(as_completed(futures), total=len(files)):
            res = future.result()
            if "Copied" in res:
                stats["Copied"] += 1
            elif "Translated" in res:
                stats["Translated"] += 1
            else:
                stats["Failed"] += 1
                print(res)
                
    print("\nDataset Standardization Complete.")
    print(f"Copied (Already English): {stats['Copied']}")
    print(f"Translated to English: {stats['Translated']}")
    print(f"Failed: {stats['Failed']}")

if __name__ == "__main__":
    main()
