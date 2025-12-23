import json
import random
import os


def generate_quote() -> str:
    """
    Generates a random quote from quotes_simplified.json.
    
    Returns:
        str: A formatted string in the format "This is a quote about {Category} by {Author}: {Quote}."
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'quotes_simplified.json')
    
    # Load the quotes from JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        quotes = json.load(f)
    
    # Select a random quote
    quote_data = random.choice(quotes)
    
    # Format the output
    category = quote_data.get('Category', 'unknown')
    author = quote_data.get('Author', 'Unknown')
    quote = quote_data.get('Quote', '')
    
    return f"This is a quote about {category} by {author}: \n{quote}."

