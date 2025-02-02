import os
import logging
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Database connection and operations handler."""
    
    def __init__(self):
        """Initialize database connection using environment variables."""
        load_dotenv()
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        self.connect()

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.create_tables()
            logger.info("Database connection established successfully")
        except (psycopg2.Error, ValueError) as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def ensure_connection(self):
        """Ensure database connection is healthy and reconnect if necessary."""
        try:
            # Test if connection is alive and not in error state
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (psycopg2.Error, AttributeError):
            logger.info("Reconnecting to database...")
            self.connect()

    def execute_transaction(self, operation):
        """Execute a database operation within a transaction."""
        self.ensure_connection()
        try:
            with self.conn:  # Automatically manages commit/rollback
                with self.conn.cursor() as cur:
                    return operation(cur)
        except psycopg2.Error as e:
            logger.error(f"Database operation failed: {e}")
            raise

    def create_tables(self) -> None:
        """Create necessary database tables if they don't exist."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_ratings (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        movie_id INTEGER NOT NULL,
                        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, movie_id)
                    )
                """)
                self.conn.commit()
                logger.info("Tables created/verified successfully")
        except psycopg2.Error as e:
            logger.error(f"Error creating tables: {e}")
            self.conn.rollback()
            raise

    def add_rating(self, user_id: str, movie_id: int, rating: int) -> None:
        """Add or update a movie rating for a user."""
        def _operation(cursor):
            cursor.execute(
                """
                INSERT INTO user_ratings (user_id, movie_id, rating)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, movie_id)
                DO UPDATE SET rating = %s, timestamp = CURRENT_TIMESTAMP
                """,
                (user_id, movie_id, rating, rating)
            )

        try:
            self.execute_transaction(_operation)
            logger.info(f"Rating added/updated for user {user_id}, movie {movie_id}")
        except psycopg2.Error as e:
            logger.error(f"Error adding rating: {e}")
            raise

    def get_user_ratings(self, user_id: str) -> List[Dict]:
        """Get all ratings for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            List of dictionaries containing movie_id and rating
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT movie_id, rating
                    FROM user_ratings
                    WHERE user_id = %s
                """, (user_id,))
                return cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error getting user ratings: {e}")
            raise

    def get_all_ratings(self, user_id=None):
        """Get all ratings, optionally filtered by user_id.
        
        Args:
            user_id (str, optional): If provided, get ratings for specific user
            
        Returns:
            List of dictionaries containing movie_id and rating
        """
        def _operation(cursor):
            if user_id:
                cursor.execute(
                    """
                    SELECT movie_id, rating 
                    FROM user_ratings 
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT user_id, movie_id, rating 
                    FROM user_ratings
                    """
                )
            
            if user_id:
                return [{'movie_id': row[0], 'rating': row[1]} for row in cursor.fetchall()]
            else:
                return [{'user_id': row[0], 'movie_id': row[1], 'rating': row[2]} for row in cursor.fetchall()]

        try:
            return self.execute_transaction(_operation)
        except psycopg2.Error:
            return []

    def __del__(self):
        """Close database connection when object is destroyed."""
        if hasattr(self, 'conn'):
            self.conn.close()