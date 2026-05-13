from google import genai
from dotenv import load_dotenv
import os
import time

load_dotenv()

client = genai.Client(api_key=os.getenv("AIzaSyCxgCbmwBG55XwWl8ivkcgAy4zBaLaUstk"))

max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents="Say hello and tell me you are ready to build DocuAgent."
        )
        print(response.text)
        break
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            retry_count += 1
            if retry_count < max_retries:
                # Extract retry delay if available, otherwise use exponential backoff
                import re
                match = re.search(r'retry in (\d+\.?\d*)', error_str)
                wait_time = int(float(match.group(1))) + 5 if match else (2 ** retry_count)
                print(f"Quota exceeded. Retrying in {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error: {error_str}")
                print("Max retries reached. Please wait and try again later.")
        else:
            print(f"Error: {error_str}")
            break