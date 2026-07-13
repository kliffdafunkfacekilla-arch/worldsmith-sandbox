import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\ai_worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key="", model_name="qwen2.5:latest"):'
new_block = '    def execute_prompt(prompt, system_instruction=None, json_schema=None, api_key="AIzaSyBDGMyqemNVuawYYNRjqr-uFjqvlcFR3IY", model_name="qwen2.5:latest"):'

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('API Key injected successfully.')
else:
    print('Could not find execute_prompt definition.')
