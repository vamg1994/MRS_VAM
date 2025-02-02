import os
from dotenv import load_dotenv
import requests
import logging

logger = logging.getLogger(__name__)

class TMDBApi:
    def __init__(self):
        """Initialize TMDB API with API key from environment variables."""
        load_dotenv()
        self.api_key = os.getenv('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")
        
        self.base_url = "https://api.themoviedb.org/3"

    def get_popular_movies(self, genre_ids=None, year_range=None, page=1):
        """Get popular movies with optional genre and year filtering."""
        try:
            url = f"{self.base_url}/movie/popular"
            params = {
                "api_key": self.api_key,
                "language": "en-US",
                "page": page
            }
            
            # Add genre filtering if specified
            if genre_ids:
                params["with_genres"] = ",".join(str(id) for id in genre_ids)
            
            # Add year range filtering if specified
            if year_range:
                start_year, end_year = year_range
                params["primary_release_date.gte"] = f"{start_year}-01-01"
                params["primary_release_date.lte"] = f"{end_year}-12-31"
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {len(data.get('results', []))} popular movies from page {page}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching popular movies: {e}")
            return {"results": []}

    def search_movies(self, query: str, year_range=None):
        """Search for movies by query string with optional year range."""
        try:
            params = {
                "api_key": self.api_key,
                "query": query,
                "language": "en-US",
                "page": 1
            }
            if year_range:
                start_year, end_year = year_range
                if start_year == end_year:
                    params["year"] = start_year
                else:
                    params["primary_release_date.gte"] = f"{start_year}-01-01"
                    params["primary_release_date.lte"] = f"{end_year}-12-31"

            response = requests.get(
                f"{self.base_url}/search/movie",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching movies: {e}")
            return {"results": []}

    def get_movie_details(self, movie_id: int):
        """Get detailed information about a specific movie."""
        try:
            response = requests.get(
                f"{self.base_url}/movie/{movie_id}",
                params={
                    "api_key": self.api_key,
                    "language": "en-US"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching movie details: {e}")
            return {}

    def get_genres(self):
        """Get list of movie genres."""
        try:
            response = requests.get(
                f"{self.base_url}/genre/movie/list",
                params={
                    "api_key": self.api_key,
                    "language": "en-US"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching genres: {e}")
            return {"genres": []}
