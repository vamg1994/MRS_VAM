import streamlit as st
from datetime import datetime
import html

def generate_user_id():
    """Generate a unique user ID based on timestamp and session state"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return st.session_state.user_id

def format_movie_card(movie):
    """Format movie information for display"""
    # Get movie details and escape them
    title = html.escape(movie.get('title', 'Unknown Title'))
    release_date = movie.get('release_date', '').split('-')[0]
    overview = html.escape(movie.get('overview', 'No overview available.')[:200] + '...')
    rating = movie.get('vote_average')
    rating_text = f"{round(float(rating), 1)}/10" if rating is not None else "N/A"

    # Start building the card HTML with minimal nesting
    card_html = '<div class="movie-card">'

    # Add poster
    if movie.get('poster_path'):
        poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
        card_html += f'<img src="{poster_url}" class="movie-poster">'

    # Add content container
    card_html += '<div class="movie-content">'

    # Add title and year
    card_html += f'<h3 class="movie-title">{title} {f"({release_date})" if release_date else ""}</h3>'

    # Add genres
    genre_names = []
    if 'genres' in movie:
        genre_names = [html.escape(g['name']) for g in movie['genres']]
    elif 'genre_ids' in movie and 'genres_dict' in st.session_state:
        genres_dict = st.session_state['genres_dict']
        genre_names = [html.escape(genres_dict[g_id]) for g_id in movie['genre_ids'] if g_id in genres_dict]

    if genre_names:
        card_html += '<div class="genre-container">'
        for genre in genre_names:
            card_html += f'<span class="genre-pill">{genre}</span>'
        card_html += '</div>'

    # Add rating
    card_html += f'<div class="movie-rating"><strong>Rating:</strong> {rating_text}</div>'

    # Add overview
    card_html += f'<div class="movie-overview">{overview}</div>'

    # Close containers
    card_html += '</div></div>'

    # Add CSS styles
    styles = """
    <style>
    .movie-card {
        background-color: #262730;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    .movie-poster {
        width: 100%;
        height: auto;
        border-radius: 10px 10px 0 0;
        display: block;
    }
    .movie-content {
        padding: 1rem;
    }
    .movie-title {
        font-size: 1.2em;
        font-weight: bold;
        color: white;
        margin: 0 0 0.5rem 0;
    }
    .genre-container {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin: 0.5rem 0;
    }
    .genre-pill {
        background-color: #808080;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        white-space: nowrap;
    }
    .movie-rating {
        margin: 0.5rem 0;
        font-size: 0.9em;
        color: white;
    }
    .movie-overview {
        font-size: 0.9em;
        line-height: 1.4;
        color: #e0e0e0;
    }
    </style>
    """

    return styles + card_html
