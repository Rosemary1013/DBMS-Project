import os
import re

templates_dir = r'd:\vsc\policy\templates'

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            
            # Step 1: Add hamburger icon right after the logo in header
            if '<header' in content and 'logo' in content and 'hamburger-btn' not in content:
                # Find the closing tag of the logo div/anchor
                logo_pattern = r'(<a href="/" class="logo">.*?</a>|<div class="logo">.*?</div>)'
                def add_hamburger(match):
                    return match.group(1) + '\n            <button class="hamburger-btn" aria-label="Toggle Navigation"><i class="ph ph-list"></i></button>'
                new_content = re.sub(logo_pattern, add_hamburger, new_content, count=1, flags=re.DOTALL)
            
            # Step 2: Add script to toggle if not already there
            script = """
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const hamburger = document.querySelector('.hamburger-btn');
            const navButtons = document.querySelector('.nav-buttons');
            const sidebar = document.querySelector('.sidebar');
            
            if (hamburger) {
                hamburger.addEventListener('click', () => {
                    if (navButtons) navButtons.classList.toggle('active-mobile-nav');
                    if (sidebar) sidebar.classList.toggle('active-mobile-nav');
                });
            }
        });
    </script>
</body>"""
            if 'hamburger-btn' in new_content and 'active-mobile-nav' not in new_content:
                new_content = new_content.replace('</body>', script)
                
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Added hamburger to {file}")
