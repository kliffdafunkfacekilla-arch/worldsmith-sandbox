import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_imports = """import sqlite3
import json"""

new_imports = """import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()"""

if old_imports in content:
    content = content.replace(old_imports, new_imports)

old_def = '    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key="AIzaSyBDGMyqemNVuawYYNRjqr-uFjqvlcFR3IY", model_name="qwen2.5:latest"):'
new_def = '    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key=None, model_name="qwen2.5:latest"):\n        if api_key is None:\n            api_key = os.getenv("GEMINI_API_KEY", "")'

if old_def in content:
    content = content.replace(old_def, new_def)
else:
    # try the empty api key one
    old_def2 = '    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key="", model_name="qwen2.5:latest"):'
    if old_def2 in content:
        content = content.replace(old_def2, new_def)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# create the .env file with the api key
env_path = r'c:\Users\krazy\Desktop\worldsmith-sandbox\.env'
with open(env_path, 'w', encoding='utf-8') as f:
    f.write('GEMINI_API_KEY=AIzaSyBDGMyqemNVuawYYNRjqr-uFjqvlcFR3IY\n')

print('Updated ai_worker.py and created .env')
