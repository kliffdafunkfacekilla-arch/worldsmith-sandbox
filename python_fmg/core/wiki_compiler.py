import os
import sys
import sqlite3
import json

class WikiCompiler:
    """
    Independent compiler that reads notes, assets, and map metadata from SQLite
    and exports a fully self-contained static HTML wiki website.
    """
    def __init__(self, db_path="lore_forge_world.db", output_dir="world_wiki"):
        self.db_path = db_path
        self.output_dir = output_dir

    def compile_wiki(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "notes"), exist_ok=True)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Fetch all notes
            cursor.execute("SELECT title, content, category FROM notes")
            notes = cursor.fetchall()
            
            # Build homepage index
            index_content = "<h1>World Lore Wiki Index</h1><ul>"
            
            for title, content, category in notes:
                # Convert WikiLinks [[Target]] to standard HTML links
                import re
                html_content = re.sub(r"\[\[(.*?)\]\]", r'<a href="\1.html">\1</a>', content)
                
                # Format simple line breaks and paragraphs
                html_content = html_content.replace("\n", "<br>")
                
                # Note page HTML
                note_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{title}</title>
                    <style>
                        body {{ font-family: sans-serif; background-color: #121214; color: #E1E1E6; padding: 40px; line-height: 1.6; }}
                        a {{ color: #04D361; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                        .nav {{ margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="nav"><a href="../index.html">← Back to Wiki Index</a></div>
                    <h1>{title}</h1>
                    <p>Category: <i>{category}</i></p>
                    <hr>
                    <div>{html_content}</div>
                </body>
                </html>
                """
                
                # Save individual note file
                safe_filename = re.sub(r'[\\/*?:"<>| ]', '_', title)
                with open(os.path.join(self.output_dir, "notes", f"{safe_filename}.html"), "w", encoding="utf-8") as f:
                    f.write(note_html)
                    
                index_content += f'<li><a href="notes/{safe_filename}.html">{title}</a> (Category: {category})</li>'
                
            index_content += "</ul>"
            
            # Save Main Index File
            main_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Worldsmith Wiki</title>
                <style>
                    body {{ font-family: sans-serif; background-color: #121214; color: #E1E1E6; padding: 40px; }}
                    a {{ color: #04D361; text-decoration: none; }}
                </style>
            </head>
            <body>
                {index_content}
            </body>
            </html>
            """
            with open(os.path.join(self.output_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(main_html)
                
            conn.close()
            return True, f"[+] Wiki successfully compiled to: {os.path.abspath(self.output_dir)}"
        except Exception as e:
            return False, str(e)
