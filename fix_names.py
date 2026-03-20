import os
import re

templates_dir = r'd:\vsc\policy\templates'

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pattern handles {{ obj.FNAME }} {{ obj.LNAME }}
            def replace_name(match):
                obj = match.group(1) # e.g. "c" or "customer"
                return f"{{{{ {obj}.FNAME }}}} {{% if {obj}.MNAME %}}{{{{ {obj}.MNAME }}}} {{% endif %}}{{{{ {obj}.LNAME }}}}"
            
            # This regex looks for {{ var.FNAME }} {{ var.LNAME }} precisely.
            new_content = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\.FNAME\s*\}\}\s*\{\{\s*\1\.LNAME\s*\}\}', replace_name, content)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated full names in {file}")

# Also update app.py so the single variable passes logic includes it properly whenever setting things manually
app_path = r'd:\vsc\policy\app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    app_code = f.read()
# Just in case there are manual concats
app_code = app_code.replace("f\"{customer['FNAME']} {customer['LNAME']}\"", "f\"{customer['FNAME']} {customer['MNAME'] + ' ' if customer['MNAME'] else ''}{customer['LNAME']}\"")
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app_code)
