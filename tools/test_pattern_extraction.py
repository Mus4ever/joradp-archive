"""
Test d'extraction des numéros depuis le formulaire avec nettoyage de l'encodage
"""

import re

# Simule le HTML avec l'encodage inhabituel
html_with_nulls = """<option value="61">61</option>
<option value="60">60</option>
<option value="59">59</option>"""

# Nettoie les octets nuls
cleaned_html = html_with_nulls.replace('\x00', '')

print("HTML original:", repr(html_with_nulls))
print("HTML nettoyé:", repr(cleaned_html))
print()

# Test le pattern
option_pattern = re.compile(r'<option[^>]*value=["\'](\d+)["\'][^>]*>(\d+)', re.IGNORECASE)
matches = option_pattern.findall(cleaned_html)
print("Matches option_pattern:", matches)

# Test pattern simple
simple_pattern = re.compile(r'>(\d{2,3})<', re.IGNORECASE)
simple_matches = simple_pattern.findall(cleaned_html)
print("Matches simple_pattern:", simple_matches)