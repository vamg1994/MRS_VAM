import streamlit as st
import pandas as pd
from src.database import Database
from src.tmdb_api import TMDBApi
from src.recommender import MovieRecommender
from src.utils import generate_user_id, format_movie_card
import os

# Configure page settings
st.set_page_config(
    page_title="VAM Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# Add custom CSS for header styling
st.markdown("""
    <style>
    .header-container {
        background: linear-gradient(90deg, rgba(38, 39, 48, 0.95) 0%, rgba(30, 30, 30, 0.95) 100%),
                    url('https://image.tmdb.org/t/p/original/tmU7GeKVybMWFButWEGl2M4GeiP.jpg');
        background-size: cover;
        background-position: center;
        background-blend-mode: overlay;
        padding: 1.5rem 0;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .header-content {
        display: flex;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    .logo-container {
        margin-right: 1.5rem;
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .logo-container img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        transition: transform 0.3s ease;
    }
    .logo-container img:hover {
        transform: scale(1.1);
    }
    .title-container {
        flex-grow: 1;
    }
    .main-title {
        color: #FFFFFF;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    div[data-testid="stDecoration"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize global services
db = Database()
tmdb = TMDBApi()

# Helper Functions
def get_genres():
    """Get movie genres and store in session state"""
    if 'genres_dict' not in st.session_state:
        genres = tmdb.get_genres()
        st.session_state['genres_dict'] = {
            genre['id']: genre['name'] 
            for genre in genres.get('genres', [])
        }
    return st.session_state['genres_dict']

def get_movie_details_batch(movie_ids):
    """Get details for multiple movies efficiently"""
    return [tmdb.get_movie_details(movie_id) for movie_id in movie_ids]

def get_filtered_popular_movies(selected_genres, year_range=None, exclude_movies=None):
    """Get and filter popular movies based on criteria with pagination"""
    filtered_movies = []
    page = 1
    max_pages = 50  # Limit API calls to avoid rate limiting
    
    while len(filtered_movies) < 8 and page <= max_pages:
        # Get movies from current page
        popular_movies = tmdb.get_popular_movies(selected_genres, year_range, page=page)
        if 'results' not in popular_movies:
            break
        
        # Filter movies from current page
        page_movies = [
            movie for movie in popular_movies['results']
            if _movie_matches_criteria(movie, selected_genres, year_range, exclude_movies)
        ]
        
        filtered_movies.extend(page_movies)
        page += 1
    
    return filtered_movies[:8]  # Return up to 8 movies

def _movie_matches_criteria(movie, selected_genres, year_range, exclude_movies):
    """Check if movie matches all filtering criteria"""
    # Skip excluded movies
    if exclude_movies and movie['id'] in exclude_movies:
        return False
        
    # Check genre filter
    if selected_genres and not any(g in selected_genres for g in movie.get('genre_ids', [])):
        return False
        
    # Check year filter
    if year_range:
        release_year = int(movie.get('release_date', '0000')[:4]) if movie.get('release_date') else 0
        if not (year_range[0] <= release_year <= year_range[1]):
            return False
            
    return True

def display_movie_grid(movies, is_rated=False, ratings=None, section="popular"):
    """Display movies in a responsive grid layout"""
    if not movies:
        return

    # Get current user ID
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Please log in first")
        return

    # Get all user ratings if not provided
    if ratings is None:
        ratings = db.get_all_ratings(user_id)

    # Display movies in a 4-column grid
    for i in range(0, len(movies), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(movies):
                _display_movie_card(col, movies[i + j], is_rated, ratings, section, i, j)

def _display_movie_card(col, movie, is_rated, ratings, section, i, j):
    """Display individual movie card with rating functionality"""
    with col:
        # Display movie image and basic info
        st.image(
            f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" 
            if movie.get('poster_path') else "static/no_poster.png"
        )
        st.subheader(f"{movie.get('title', 'Unknown Title')} ({movie.get('release_date', '')[:4]})")
        
        # Display genres
        _display_genres(movie)
        
        # Display rating and overview
        rating = movie.get('vote_average')
        st.text(f"Rating: {round(float(rating), 1)}/10" if rating else "N/A")
        
        overview = movie.get('overview', 'No overview available.')
        st.text(overview[:200] + '...' if len(overview) > 200 else overview)
        
        # Handle movie rating
        _handle_movie_rating(movie, is_rated, ratings, section, i, j)

def _display_genres(movie):
    """Display movie genres"""
    genre_names = []
    if 'genres' in movie:
        genre_names = [g['name'] for g in movie['genres']]
    elif 'genre_ids' in movie and 'genres_dict' in st.session_state:
        genres_dict = st.session_state['genres_dict']
        genre_names = [genres_dict[g_id] for g_id in movie['genre_ids'] if g_id in genres_dict]
    
    if genre_names:
        st.caption(", ".join(genre_names))

def _handle_movie_rating(movie, is_rated, ratings, section, i, j):
    """Handle movie rating interface and logic"""
    if is_rated and ratings:
        rating = next((r['rating'] for r in ratings if r['movie_id'] == movie['id']), None)
        if rating:
            st.text(f"Your Rating: {rating}/5")
    else:
        st.text("Rate:")
        st.caption("Click a number to rate")
        
        # Display rating buttons
        rating_cols = st.columns(5)
        for rating in range(1, 6):
            with rating_cols[rating-1]:
                if st.button(f"{rating}", key=f"rate_{movie['id']}_{rating}_{section}_{i}_{j}"):
                    _submit_rating(movie['id'], rating, section)

def _submit_rating(movie_id, rating, section):
    """Submit user rating and update state"""
    db.add_rating(st.session_state.user_id, movie_id, rating)
    
    # Update rated movies set
    if section == "popular":
        st.session_state.rated_popular_movies.add(movie_id)
    elif section == "recommendations":
        st.session_state.rated_recommendation_movies.add(movie_id)
    
    st.success("Rating submitted!")
    st.experimental_rerun()

def main():
    """Main application function"""
    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state.user_id = generate_user_id()
    if 'rated_popular_movies' not in st.session_state:
        st.session_state.rated_popular_movies = set()
    if 'rated_recommendation_movies' not in st.session_state:
        st.session_state.rated_recommendation_movies = set()
    if 'show_search_results' not in st.session_state:
        st.session_state.show_search_results = True

    # Application header
    st.title("Movie Recommender System")
    get_genres()

    # Sidebar with filters and contact information
    with st.sidebar:
        # Add contact information at the top of sidebar
        st.markdown("### Virgilio Madrid - Data Scientist")
        st.markdown("[Portfolio 🌐](https://portfolio-vam.vercel.app/)")
        st.markdown("[LinkedIn 💼](https://www.linkedin.com/in/vamadrid/)")
        st.markdown("[E-Mail 📧](mailto:virgiliomadrid1994@gmail.com)")
        
        # Separator
        st.markdown("---")
        
        # Existing filters
        year_range, selected_genres = _create_sidebar_filters()

    # Search functionality
    _handle_search(selected_genres, year_range)

    # Main content tabs
    _create_main_tabs(selected_genres, year_range)

def _create_sidebar_filters():
    """Create and return sidebar filters"""
    st.header("Filters")
    
    # Year range slider
    current_year = 2024
    st.subheader("Release Year")
    year_range = st.slider(
        "Select year range",
        min_value=1900,
        max_value=current_year,
        value=(1900, current_year),
        step=1
    )
    
    # Genre selection
    st.subheader("Genres")
    selected_genres = []
    col1, col2 = st.columns(2)
    
    sorted_genres = sorted(get_genres().items(), key=lambda x: x[1])
    half = len(sorted_genres) // 2
    
    with col1:
        for genre_id, genre_name in sorted_genres[:half]:
            if st.checkbox(genre_name, key=f"genre_{genre_id}"):
                selected_genres.append(genre_id)
    
    with col2:
        for genre_id, genre_name in sorted_genres[half:]:
            if st.checkbox(genre_name, key=f"genre_{genre_id}"):
                selected_genres.append(genre_id)
                
    return year_range, selected_genres

def _handle_search(selected_genres, year_range):
    """Handle movie search functionality"""
    search_query = st.text_input("Enter movie name", key="main_search")
    
    if search_query:
        if st.button("Show/Hide Results"):
            st.session_state.show_search_results = not st.session_state.show_search_results
            st.experimental_rerun()
    
    if search_query and st.session_state.show_search_results:
        _display_search_results(search_query, selected_genres, year_range)

def _display_search_results(search_query, selected_genres, year_range):
    """Display search results with filtering"""
    st.subheader("Search Results")
    search_results = tmdb.search_movies(search_query, year_range)
    
    if 'results' in search_results and search_results['results']:
        filtered_results = [
            movie for movie in search_results['results'][:8]
            if _movie_matches_criteria(movie, selected_genres, year_range, None)
        ]
        
        if filtered_results:
            display_movie_grid(filtered_results, section="search")
        else:
            st.info("No movies found matching your filters.")
    else:
        st.info("No movies found for your search query.")

def _create_main_tabs(selected_genres, year_range):
    """Create and handle main content tabs"""
    tab1, tab2, tab3 = st.tabs(["Popular Movies", "Recommendations", "Rated Movies"])
    
    with tab1:
        _handle_popular_movies_tab(selected_genres, year_range)
    
    with tab2:
        _handle_recommendations_tab(selected_genres, year_range)
    
    with tab3:
        _handle_rated_movies_tab(selected_genres, year_range)

def _handle_popular_movies_tab(selected_genres, year_range):
    """Handle Popular Movies tab content"""
    st.header("Popular Movies")
    
    # Show loading indicator
    with st.spinner('Loading popular movies...'):
        filtered_movies = get_filtered_popular_movies(
            selected_genres,
            year_range,
            exclude_movies=st.session_state.rated_popular_movies
        )
    
    if filtered_movies:
        display_movie_grid(filtered_movies, section="popular")
    else:
        st.info("No movies found matching your filters. Try adjusting your criteria.")

def _handle_recommendations_tab(selected_genres, year_range):
    """Handle Recommendations tab content"""
    st.header("Your Recommendations")
    user_ratings = db.get_user_ratings(st.session_state.user_id)
    
    if not user_ratings:
        st.info("Start rating movies to get personalized recommendations!")
        return
        
    _process_recommendations(user_ratings, selected_genres, year_range)

def _process_recommendations(user_ratings, selected_genres, year_range):
    """Process and display movie recommendations"""
    all_ratings = db.get_all_ratings()
    recommender = MovieRecommender(all_ratings)
    
    rated_movie_ids = list(set([r['movie_id'] for r in all_ratings]))
    movie_details = get_movie_details_batch(rated_movie_ids)
    
    recommendations, message = recommender.get_recommendations(
        st.session_state.user_id,
        n_recommendations=12,
        movie_data=movie_details
    )
    
    if recommendations:
        _display_filtered_recommendations(recommendations, selected_genres, year_range)
    else:
        st.info(message)

def _display_filtered_recommendations(recommendations, selected_genres, year_range):
    """Display filtered movie recommendations"""
    filtered_recommendations = []
    for movie_id in recommendations:
        if movie_id not in st.session_state.rated_recommendation_movies:
            movie_details = tmdb.get_movie_details(movie_id)
            if _movie_matches_criteria(movie_details, selected_genres, year_range, None):
                filtered_recommendations.append(movie_details)
    
    if filtered_recommendations:
        display_movie_grid(filtered_recommendations[:8], section="recommendations")
    else:
        st.info("No recommendations found matching your genre and year preferences.")

def _handle_rated_movies_tab(selected_genres, year_range):
    """Handle Rated Movies tab content"""
    st.header("Your Highly Rated Movies")
    user_ratings = db.get_user_ratings(st.session_state.user_id)
    
    if not user_ratings:
        st.info("Start rating movies to see your favorites here!")
        return
        
    _display_rated_movies(user_ratings, selected_genres, year_range)

def _display_rated_movies(user_ratings, selected_genres, year_range):
    """Display user's rated movies with filtering"""
    high_rated_movies = [rating for rating in user_ratings if rating['rating'] >= 4]
    
    if not high_rated_movies:
        st.info("You haven't rated any movies 4 stars or higher yet!")
        return
        
    movie_details = []
    for rating in high_rated_movies:
        movie = tmdb.get_movie_details(rating['movie_id'])
        if _movie_matches_criteria(movie, selected_genres, year_range, None):
            movie_details.append(movie)
    
    if movie_details:
        display_movie_grid(movie_details, is_rated=True, ratings=high_rated_movies, section="rated")
    else:
        st.info("No highly rated movies match your genre and year preferences.")

if __name__ == "__main__":
    main()
