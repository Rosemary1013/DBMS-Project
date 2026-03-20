import os
import re

templates_dir = r'd:\vsc\policy\templates'

flash_html = """    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="flash-overlay {% if category == 'error' %}flash-error{% else %}flash-success{% endif %}">
            <i class="ph-bold {% if category == 'error' %}ph-warning-circle{% else %}ph-check-circle{% endif %} flash-icon"></i>
            <span>{{ message }}</span>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}"""

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pattern to match the existing flash message block, which varies slightly with spacing but has the inline style.
            # We look for the whole {% with messages ... endwith %} block containing inline styles.
            pattern = r'\{\%\s*with messages = get_flashed_messages.*?\{\%\s*endwith\s*\%\}'
            
            if re.search(pattern, content, re.DOTALL):
                new_content = re.sub(pattern, flash_html.strip(), content, flags=re.DOTALL)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated flash messages in {file}")
