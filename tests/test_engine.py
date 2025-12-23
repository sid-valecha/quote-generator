"""Simple test script for the quote engine."""

import sys
import os

# Add the parent directory to the path so we can import from engines
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.quote_engine import generate_quote

if __name__ == "__main__":
    print("Generating a random quote...\n")
    print(generate_quote())
