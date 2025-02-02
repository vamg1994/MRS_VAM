"""Configuration settings for the Movie Recommender System."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # TMDB API
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    
    # Redis Cache
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Cache TTL (in seconds)
    MOVIE_CACHE_TTL = 86400  # 24 hours
    POPULAR_MOVIES_TTL = 3600  # 1 hour
    
    # Session
    SESSION_TTL = 86400  # 24 hours
    
    # Paths
    ROOT_DIR = Path(__file__).parent.parent
    STATIC_DIR = ROOT_DIR / 'static' 