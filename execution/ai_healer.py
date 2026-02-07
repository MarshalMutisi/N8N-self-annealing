import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_working_model():
    """Try to find a working model from the available list."""
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro',
        'models/gemini-1.5-flash-latest',
        'models/gemini-1.5-pro-latest'
    ]
    
    for name in candidates:
        try:
            model = genai.GenerativeModel(name)
            # Simple test generation to verify access
            model.generate_content("test")
            print(f"✅ Found working model: {name}")
            return model
        except Exception as e:
            # print(f"⚠️ Model {name} failed: {e}")
            continue
            
    print("❌ No working Gemini models found.")
    return None

def consult_gemini_for_fix(workflow_json: dict, error_msg: str) -> tuple[bool, str, dict]:
    """
    Sends the broken workflow and error to Gemini to generate a fix.
    Returns: (success, explanation, fixed_workflow_json)
    """
    if not GEMINI_API_KEY:
        return False, "No Gemini API Key found", {}

    # Improve: Cache the working model? For now, re-instantiating is fine.
    # To avoid delay, we will just try the main ones without pre-test in the real detailed call
    # But let's use a simpler list directly.
    
    candidates = [
        'gemini-2.0-flash-exp', 
        'gemini-1.5-flash', 
        'gemini-1.5-pro', 
        'gemini-pro',
        'gemini-3-flash-preview'
    ]
    
    prompt = f"""
    You are an expert n8n Workflow Doctor.
    
    Here is a BROKEN n8n workflow (JSON) and the error message it produced.
    
    ERROR: "{error_msg}"
    
    WORKFLOW JSON:
    {json.dumps(workflow_json)}
    
    TASK:
    1. Identify which node is causing the error.
    2. Fix the configuration of that node (or add a node if needed).
    3. Return the FULLY CORRECTED workflow JSON.
    4. Provide a very brief explanation of what you fixed.
    
    RESPONSE FORMAT:
    You must return a JSON object with this exact structure:
    {{
        "explanation": "Fixed typo in HTTP Request URL...",
        "fixed_workflow": {{ ...full valid n8n workflow json... }}
    }}
    
    Do not wrap in markdown code blocks. Return RAW JSON only.
    """

    last_error = ""
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up markdown if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            result = json.loads(text)
            return True, result["explanation"], result["fixed_workflow"]
            
        except Exception as e:
            last_error = str(e)
            continue
            
    return False, f"All Gemini models failed. Last error: {last_error}", {}
