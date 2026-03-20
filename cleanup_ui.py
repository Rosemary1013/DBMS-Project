import os
import re

templates_dir = r'd:\vsc\policy\templates'
static_dir = r'd:\vsc\policy\static'

# Colors to replace
replacements = {
    'color: white;': 'color: var(--text);',
    'color:white;': 'color: var(--text);',
    'background: white;': 'background: var(--card-bg);',
    'rgba(255, 255, 255, 0.01)': 'rgba(30, 41, 59, 0.3)',
    'rgba(255, 255, 255, 0.02)': 'rgba(30, 41, 59, 0.4)',
    'rgba(255, 255, 255, 0.03)': 'rgba(30, 41, 59, 0.5)',
    'rgba(255, 255, 255, 0.05)': 'rgba(30, 41, 59, 0.6)',
    'pt: 1.5rem;': 'padding-top: 1.5rem;',
    '?{{ policy.PREM_AMT }}': '₹{{ policy.PREM_AMT }}',
}

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {file}")

# Update master.css one last time for absolute darkness
with open(os.path.join(static_dir, 'master.css'), 'r', encoding='utf-8') as f:
    css = f.read()

# Ensure no absolute white in CSS
css = css.replace('#ffffff', '#f1f5f9')
css = css.replace('white', '#f1f5f9')

with open(os.path.join(static_dir, 'master.css'), 'w', encoding='utf-8') as f:
    f.write(css)
