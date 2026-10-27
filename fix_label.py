import re
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix label setup
content = re.sub(
    r'self\.internet_status_label = QLabel\([^\)]+\)',
    r'self.internet_status_label = QLabel("● CHECKING...")',
    content
)

content = content.replace(
    'self.internet_status_label.setStyleSheet("color: #ffa500;") # Orange while checking',
    'self.internet_status_label.setStyleSheet("color: #ffa500; font-weight: bold; border: 1px solid #ffa500; padding: 2px 6px; border-radius: 3px;") # Orange while checking'
)

# Fix update_internet_status method online
content = re.sub(
    r'self\.internet_status_label\.setText\([^)]+"[^"]*ONLINE"\)',
    r'self.internet_status_label.setText("● CONNECTED")',
    content
)

content = re.sub(
    r'self\.internet_status_label\.setStyleSheet\("color: #00ff41; border: 1px solid #00ff41;"\)',
    r'self.internet_status_label.setStyleSheet("color: #00ff41; font-weight: bold; border: 1px solid #00ff41; padding: 2px 6px; border-radius: 3px;")',
    content
)

# Fix update_internet_status method offline
content = re.sub(
    r'self\.internet_status_label\.setText\([^)]+"[^"]*OFFLINE"\)',
    r'self.internet_status_label.setText("● DISCONNECTED")',
    content
)

# Actually there is no stylesheet on the OFFLINE state originally in the code, wait, let me check.
# Let's just add it.
content = re.sub(
    r'self\.internet_status_label\.setText\("● DISCONNECTED"\)',
    r'self.internet_status_label.setText("● DISCONNECTED")\n            self.internet_status_label.setStyleSheet("color: #ff3131; font-weight: bold; border: 1px solid #ff3131; padding: 2px 6px; border-radius: 3px;")',
    content
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)
