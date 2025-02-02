import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class NLPRecommender:
    def __init__(self):
        self.tfidf = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        self.movie_tfidf_matrix = None
        self.movie_ids = None
        self.movie_descriptions = None

    def fit(self, movie_data):
        """
        Fit the TF-IDF vectorizer on movie descriptions
        
        Args:
            movie_data: List of dictionaries containing movie information
                       Each dict should have 'id' and 'overview' keys
        """
        try:
            # Extract movie descriptions and IDs
            valid_movies = [(movie['id'], movie.get('overview', '')) 
                          for movie in movie_data 
                          if movie.get('overview')]
            
            if not valid_movies:
                logger.warning("No valid movie descriptions found")
                return
            
            self.movie_ids, self.movie_descriptions = zip(*valid_movies)
            
            # Create TF-IDF matrix
            self.movie_tfidf_matrix = self.tfidf.fit_transform(self.movie_descriptions)
            logger.info(f"Created TF-IDF matrix with shape: {self.movie_tfidf_matrix.shape}")
            
        except Exception as e:
            logger.error(f"Error in fitting NLP recommender: {str(e)}")
            self.movie_tfidf_matrix = None
            self.movie_ids = None
            self.movie_descriptions = None

    def get_similar_movies(self, movie_id, n_recommendations=5):
        """
        Get similar movies based on description similarity
        
        Args:
            movie_id: ID of the movie to find similarities for
            n_recommendations: Number of similar movies to return
            
        Returns:
            List of similar movie IDs
        """
        try:
            if self.movie_tfidf_matrix is None:
                logger.warning("TF-IDF matrix not initialized")
                return []
            
            # Find movie index
            if movie_id not in self.movie_ids:
                logger.warning(f"Movie ID {movie_id} not found in the matrix")
                return []
            
            movie_idx = self.movie_ids.index(movie_id)
            
            # Calculate similarity scores
            movie_vector = self.movie_tfidf_matrix[movie_idx]
            similarity_scores = cosine_similarity(movie_vector, self.movie_tfidf_matrix)
            
            # Get indices of similar movies (excluding the input movie)
            similar_indices = similarity_scores.argsort()[0][::-1][1:n_recommendations+1]
            
            # Convert indices to movie IDs
            similar_movies = [self.movie_ids[idx] for idx in similar_indices]
            
            return similar_movies
            
        except Exception as e:
            logger.error(f"Error in getting similar movies: {str(e)}")
            return []
