import json
import re
import os

ts_file = r"C:\Users\krazy\Desktop\Fantasy-Map-Generator\src\modules\names-generator.ts"
py_file = r"C:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\core\namebases_data.py"

def extract():
    with open(ts_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the getNameBases() function
    match = re.search(r'getNameBases\(\):\s*NameBase\[\]\s*\{.*?return\s*(\[.*?\]);\s*\}', content, re.DOTALL)
    if not match:
        print("Could not find namebases array")
        return

    array_str = match.group(1)
    # The JS array contains unquoted keys. We need to format it to JSON.
    # Replace keys like `name:` with `"name":`
    json_str = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', array_str)
    # Remove single line comments
    json_str = re.sub(r'//.*', '', json_str)
    # Remove trailing commas
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

    try:
        data = json.loads(json_str)
        
        with open(py_file, 'w', encoding='utf-8') as out:
            out.write("NAMEBASES = ")
            out.write(json.dumps(data, indent=4))
        print(f"Successfully extracted {len(data)} namebases to {py_file}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        # fallback string manipulation if JSON parse fails due to complex JS
        with open("raw_namebases.txt", "w", encoding='utf-8') as temp:
            temp.write(json_str)

if __name__ == "__main__":
    extract()
