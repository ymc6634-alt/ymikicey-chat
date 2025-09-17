from dotenv import load_dotenv
import os

load_dotenv()
print("Loaded key:", os.getenv("OPENAI_API_KEY"))
