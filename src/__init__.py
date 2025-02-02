# Empty file to mark directory as Python package 

"""
Movie Recommender System
A portfolio project demonstrating recommendation algorithms and best practices.
"""

from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.parent

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) 