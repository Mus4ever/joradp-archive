"""
Examen de la structure réelle du HTML AR 2026 pour comprendre l'encodage
"""

with open("ar_2026_python_client.html", "rb") as f:
    raw_content = f.read()

print("Taille brute:", len(raw_content))
print("Premiers 100 octets (hex):", raw_content[:100].hex())
print()

# Cherche les null bytes
null_count = raw_content.count(b'\x00')
print("Nombre de \\x00:", null_count)
print()

# Extrait une section autour des options
html_str = raw_content.decode('utf-8', errors='ignore')
print("Taille après décodage:", len(html_str))

# Cherche "option" dans le HTML décodé
option_positions = []
for i, char in enumerate(html_str):
    if i < len(html_str) - 5 and html_str[i:i+6].lower() == 'option':
        option_positions.append(i)

print(f"Positions de 'option': {len(option_positions)}")
if option_positions:
    for pos in option_positions[:5]:
        context = html_str[max(0, pos-20):min(len(html_str), pos+50)]
        print(f"  Position {pos}: ...{context}...")