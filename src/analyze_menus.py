import os
from pathlib import Path
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def extract_text_from_pdfs(menu_dir):
    text_content = ""
    pdf_files = list(Path(menu_dir).rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF menus in {menu_dir}...")
    
    import random
    if len(pdf_files) > 50:
        pdf_files = random.sample(pdf_files, 50)
        
    for p in pdf_files:
        try:
            reader = PdfReader(p)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            text_content += "\n--- END OF MENU ---\n\n"
        except Exception as e:
            print(f"Skipping {p.name}: {e}")
            
    return text_content

def main():
    menu_dir = Path("../../ALL MENU")
    if not menu_dir.exists():
        print(f"Menu directory not found: {menu_dir.resolve()}")
        return

    print("Extracting text from menus...")
    menu_text = extract_text_from_pdfs(menu_dir)
    
    print(f"Extracted {len(menu_text)} characters of menu data.")
    
    prompt = f"""
    You are an expert culinary strategist and menu designer. 
    Below is a massive collection of raw menu text extracted from a private chef's past event PDFs.
    
    Analyze these menus and extract a comprehensive "Chef's Style Guide".
    I want you to write a detailed markdown guide that explains:
    1. Overall Culinary Philosophy (What cuisines, techniques, and aesthetic do they lean towards?)
    2. Menu Structure (How many courses usually? Do they do amuse-bouche? How do they structure their progression from starter to dessert?)
    3. Ingredient Preferences (What proteins, premium ingredients, or flavor pairings show up repeatedly?)
    4. Textural & Balancing Rules (How do they balance heavy vs light elements across courses?)
    
    This guide will be used later as a system prompt to autonomously generate NEW menus in this exact style. Be exhaustive and professional.
    
    PAST MENUS:
    {menu_text[:250000]} # Limit characters just in case
    """
    
    print("Asking Gemini to analyze the chef's style (this may take a minute)...")
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    
    output_path = Path("data/chef_style_guide.md")
    output_path.write_text(response.text)
    
    print(f"\n✅ Style Guide created successfully at {output_path}!")

if __name__ == "__main__":
    main()
