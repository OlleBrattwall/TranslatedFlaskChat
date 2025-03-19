import deepl
from dotenv import load_dotenv
import os

load_dotenv()

auth_key = os.getenv("TRANS_API_KEY")  # Replace with your key
translator = deepl.Translator(auth_key)

def translate_text(content, target_language):

    try:
        result = translator.translate_text(content, target_lang=target_language.upper())
        return str(result)
    except Exception as e:
        print(f"Translation error: {e}")
        return content