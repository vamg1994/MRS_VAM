import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
from .nlp_recommender import NLPRecommender

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieRecommender:
    def __init__(self, ratings_data):
        self.ratings_df = pd.DataFrame(ratings_data)
        self.user_movie_matrix = None
        self.item_similarity_matrix = None
        self.user_similarity_matrix = None
        self.nlp_recommender = NLPRecommender()
        self.MIN_RATINGS_REQUIRED = 3
        self.MIN_RATING_THRESHOLD = 4
        self._prepare_data()

    def _prepare_data(self):
        """Prepare the user-movie matrix and calculate similarity matrices"""
        try:
            if self.ratings_df.empty:
                logger.warning("No ratings data available")
                return

            logger.info(f"Preparing data with {len(self.ratings_df)} ratings")
            
            # Create user-movie matrix
            self.user_movie_matrix = self.ratings_df.pivot(
                index='user_id',
                columns='movie_id',
                values='rating'
            ).fillna(0)

            if self.user_movie_matrix.empty:
                logger.warning("Empty user-movie matrix")
                return

            # Normalize ratings using Z-score normalization
            self.normalized_matrix = (self.user_movie_matrix - self.user_movie_matrix.mean()) / self.user_movie_matrix.std()
            self.normalized_matrix = self.normalized_matrix.fillna(0)
            
            logger.info(f"Created matrix with shape: {self.normalized_matrix.shape}")
            
            # Calculate user similarity matrix
            self.user_similarity_matrix = cosine_similarity(self.normalized_matrix)
            
            # Calculate item similarity matrix
            self.item_similarity_matrix = cosine_similarity(self.normalized_matrix.T)
            
            logger.info("Similarity matrices calculated successfully")
            
        except Exception as e:
            logger.error(f"Error in data preparation: {str(e)}")
            self.user_movie_matrix = None
            self.user_similarity_matrix = None
            self.item_similarity_matrix = None

    def _get_user_based_recommendations(self, user_id, n_recommendations=5):
        try:
            user_idx = self.user_movie_matrix.index.get_loc(user_id)
            user_similarities = self.user_similarity_matrix[user_idx]
            similar_users = np.argsort(user_similarities)[::-1][1:6]  # Get top 5 similar users
            
            recommendations = {}
            rated_movies = self.ratings_df[self.ratings_df['user_id'] == user_id]['movie_id'].tolist()
            
            for similar_user_idx in similar_users:
                similar_user_id = self.user_movie_matrix.index[similar_user_idx]
                similar_user_ratings = self.ratings_df[self.ratings_df['user_id'] == similar_user_id]
                
                for _, rating in similar_user_ratings.iterrows():
                    if rating['movie_id'] not in rated_movies:
                        if rating['movie_id'] not in recommendations:
                            recommendations[rating['movie_id']] = rating['rating'] * user_similarities[similar_user_idx]
                        else:
                            recommendations[rating['movie_id']] += rating['rating'] * user_similarities[similar_user_idx]
            
            return sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        except Exception as e:
            logger.error(f"Error in user-based recommendations: {str(e)}")
            return []

    def _get_item_based_recommendations(self, user_id, n_recommendations=5):
        try:
            user_ratings = self.ratings_df[self.ratings_df['user_id'] == user_id]
            recommendations = {}
            
            for _, rating in user_ratings.iterrows():
                movie_idx = self.user_movie_matrix.columns.get_loc(rating['movie_id'])
                similar_items = np.argsort(self.item_similarity_matrix[movie_idx])[::-1][1:6]
                
                for similar_item_idx in similar_items:
                    similar_movie_id = self.user_movie_matrix.columns[similar_item_idx]
                    if similar_movie_id not in user_ratings['movie_id'].values:
                        similarity_score = self.item_similarity_matrix[movie_idx][similar_item_idx]
                        if similar_movie_id not in recommendations:
                            recommendations[similar_movie_id] = rating['rating'] * similarity_score
                        else:
                            recommendations[similar_movie_id] += rating['rating'] * similarity_score
            
            return sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        except Exception as e:
            logger.error(f"Error in item-based recommendations: {str(e)}")
            return []

    def update_nlp_data(self, movie_data):
        """Update the NLP recommender with new movie data"""
        self.nlp_recommender.fit(movie_data)

    def _get_content_based_recommendations(self, user_ratings, n_recommendations=5):
        """Get recommendations based on movie content similarity"""
        try:
            content_recommendations = {}
            
            # Get recommendations based on each highly-rated movie
            for _, row in user_ratings[user_ratings['rating'] >= self.MIN_RATING_THRESHOLD].iterrows():
                similar_movies = self.nlp_recommender.get_similar_movies(row['movie_id'])
                for movie_id in similar_movies:
                    if movie_id not in content_recommendations:
                        content_recommendations[movie_id] = row['rating']
                    else:
                        content_recommendations[movie_id] = max(content_recommendations[movie_id], row['rating'])
            
            return sorted(content_recommendations.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        except Exception as e:
            logger.error(f"Error in content-based recommendations: {str(e)}")
            return []

    def get_recommendations(self, user_id: str, n_recommendations: int = 5, movie_data=None):
        """Get hybrid movie recommendations combining collaborative and content-based approaches"""
        try:
            if self.user_movie_matrix is None or self.user_similarity_matrix is None:
                logger.warning("Recommendation system not properly initialized")
                return [], "System not properly initialized. Please try again later."

            if user_id not in self.user_movie_matrix.index:
                logger.warning(f"User {user_id} not found in the matrix")
                return [], "No ratings found for this user."

            user_ratings = self.ratings_df[self.ratings_df['user_id'] == user_id]
            user_ratings_count = len(user_ratings)
            
            if user_ratings_count < self.MIN_RATINGS_REQUIRED:
                logger.info(f"User {user_id} has insufficient ratings: {user_ratings_count}")
                return [], f"Please rate at least {self.MIN_RATINGS_REQUIRED} movies to get recommendations."

            # Update NLP data if provided
            if movie_data:
                self.update_nlp_data(movie_data)

            # Get recommendations from all approaches
            user_based_recs = self._get_user_based_recommendations(user_id, n_recommendations)
            item_based_recs = self._get_item_based_recommendations(user_id, n_recommendations)
            content_based_recs = self._get_content_based_recommendations(user_ratings, n_recommendations)

            # Combine recommendations with weights
            USER_WEIGHT = 0.4
            ITEM_WEIGHT = 0.3
            CONTENT_WEIGHT = 0.3

            combined_recs = {}
            
            for movie_id, score in user_based_recs:
                combined_recs[movie_id] = score * USER_WEIGHT

            for movie_id, score in item_based_recs:
                if movie_id in combined_recs:
                    combined_recs[movie_id] += score * ITEM_WEIGHT
                else:
                    combined_recs[movie_id] = score * ITEM_WEIGHT

            for movie_id, score in content_based_recs:
                if movie_id in combined_recs:
                    combined_recs[movie_id] += score * CONTENT_WEIGHT
                else:
                    combined_recs[movie_id] = score * CONTENT_WEIGHT

            # Sort and get final recommendations
            final_recommendations = sorted(combined_recs.items(), key=lambda x: x[1], reverse=True)
            recommendations = [movie_id for movie_id, _ in final_recommendations[:n_recommendations]]

            if not recommendations:
                return [], "No recommendations found based on your ratings."

            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations, "Success"

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return [], "Error generating recommendations. Please try again later."
