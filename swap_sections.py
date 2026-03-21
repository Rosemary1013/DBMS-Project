import os

file_path = r'd:\vsc\policy\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Get the two blocks of HTML
policies_start = content.find('<section id="policies-section"')
policies_end = content.find('</section>', policies_start) + len('</section>')
policies_html = content[policies_start:policies_end]

guidelines_start = content.find('<!-- Guidelines Section -->\n        <section id="guidelines"')
guidelines_end = content.find('</section>', guidelines_start) + len('</section>')
guidelines_html = content[guidelines_start:guidelines_end]

# If we found both blocks, swap them
if policies_start != -1 and guidelines_start != -1:
    # Build new string
    new_content = content[:policies_start] + guidelines_html + '\n\n        ' + policies_html + content[guidelines_end:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Swapped sections successfully!")
else:
    print(f"Could not find one of the blocks. P: {policies_start}, G: {guidelines_start}")
