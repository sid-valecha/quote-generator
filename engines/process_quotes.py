import json
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, 'quotes.json')
output_path = os.path.join(script_dir, 'quotes_simplified.json')

# Read the original quotes.json file
with open(input_path, 'r', encoding='utf-8') as f:
    quotes = json.load(f)

# Filter out Tags and Popularity, keep only Quote, Author, and Category
filtered_quotes = []
for quote in quotes:
    filtered_quote = {
        "Quote": quote.get("Quote", ""),
        "Author": quote.get("Author", ""),
        "Category": quote.get("Category", "")
    }
    filtered_quotes.append(filtered_quote)

# Write to a new JSON file
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(filtered_quotes, f, indent=2, ensure_ascii=False)

print(f"Processed {len(filtered_quotes)} quotes")
print("Created quotes_simplified.json with only Quote, Author, and Category fields")

