import os
import re

templates_dir = r'd:\vsc\policy\templates'

replacements = {
    # Navigation & General
    r'System Overview': 'Dashboard Home',
    r'Settlement Nodes': 'My Claims',
    r'Transaction Ledger': 'Payment History',
    r'Transaction History': 'Payment History',
    r'My Portfolio': 'My Policies',
    r'Active Node': 'Active Policy',
    r'protection profile': 'insurance policy',
    r'elite protection portfolio': 'insurance policies',
    r'clinical protection': 'insurance',
    r'Elite standard in digital insurance': 'Simple digital insurance',
    r'Premier Protection Plans': 'Available Insurance Plans',
    r'Portfolio Performance': 'Agent Performance',
    r'Pending Decision': 'Pending Review',
    r'System Status': 'System Health',
    
    # Customer Dashboard
    r'Protection Value': 'Total Coverage',
    r'Active Coverages': 'Active Policies',
    r'Node ID': 'Policy ID',
    r'Coverage Node': 'Insurance Policy',
    r'Core Metrics & Performance': 'Key Metrics',
    r'Policy Issuance Verification': 'Policy Verifications',
    
    # Agent & Admin
    r'Client Portfolio': 'My Clients',
    r'Client Claims': 'Client Claims',
    r'Admin High Command': 'Admin Portal',
    r'High Command': 'Portal',
    r'Agent Gate': 'Agent Access',
    r'Agent Terminal': 'Agent Dashboard',
    
    # Actions
    r'Abandon Enrollment': 'Cancel',
    r'Authorize & Activate Policy': 'Complete Purchase',
    r'Enter Dashboard': 'Log In',
    r'Return Home': 'Back to Home',
}

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content
            for old, new in replacements.items():
                new_content = re.sub(old, new, new_content, flags=re.IGNORECASE)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated terms in {file}")
