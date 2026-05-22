import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ==========================================
# 1. Page Configuration & Custom CSS
# ==========================================
st.set_page_config(page_title="Spotify Artists Dashboard", layout="wide", page_icon="🎵")

# Injecting Custom CSS to style the dashboard
st.markdown("""
    <style>
    /* Main background and fonts */
    .stApp {
        background-color: #f4f6f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Custom Header Styling */
    .main-header {
        background: linear-gradient(90deg, #1DB954 0%, #191414 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Custom Metric Cards */
    div[data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: black;
        border-right: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. Data Loading & Preprocessing
# ==========================================
@st.cache_data
def load_data():
    # Load the CSV file
    df = pd.read_csv('./source/scrap.csv')
    
    # Clean numeric columns (handle any non-numeric coercions)
    numeric_cols = ['monthly_listeners', 'popularity', 'followers', 'last_release', 'num_releases', 'num_tracks']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Drop rows without a valid last_release year
    df = df.dropna(subset=['last_release'])
    df['last_release'] = df['last_release'].astype(int)
    
    # Clean string columns
    df['names'] = df['names'].fillna('Unknown Artist').astype(str)
    df['genres'] = df['genres'].fillna('Unknown')
    
    return df

df = load_data()

# Extract all unique genres for the slicer
all_genres = set()
for genre_string in df['genres']:
    if isinstance(genre_string, str):
        # Split by comma and strip whitespace
        genres = [g.strip() for g in genre_string.split(',')]
        all_genres.update(genres)
unique_genres = sorted(list(all_genres))


# ==========================================
# 3. Sidebar Filters / Slicers
# ==========================================
st.sidebar.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png", width=150)
st.sidebar.markdown("### 🎛️ Dashboard Filters")

# Filter 1: Genres
selected_genres = st.sidebar.multiselect(
    "Filter by Genre(s):",
    options=unique_genres,
    help="Select one or more genres to filter the artists."
)

# Filter 2: Names
selected_names = st.sidebar.multiselect(
    "Filter by Artist Name:",
    options=sorted(df['names'].unique()),
    help="Select specific artists to view."
)

# Filter 3: Last Release
min_year = int(df['last_release'].min())
max_year = int(df['last_release'].max())
selected_years = st.sidebar.slider(
    "Filter by Last Release Year:",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)

# ==========================================
# 4. Apply Filters to Data
# ==========================================
filtered_df = df.copy()

# Apply Year filter
filtered_df = filtered_df[
    (filtered_df['last_release'] >= selected_years[0]) & 
    (filtered_df['last_release'] <= selected_years[1])
]

# Apply Name filter
if selected_names:
    filtered_df = filtered_df[filtered_df['names'].isin(selected_names)]

# Apply Genre filter (Check if any selected genre exists in the comma-separated string)
if selected_genres:
    def genre_match(genre_str):
        if not isinstance(genre_str, str): return False
        artist_genres = [g.strip() for g in genre_str.split(',')]
        # Returns True if ANY of the selected genres are in the artist's genres
        return any(g in artist_genres for g in selected_genres)
        
    filtered_df = filtered_df[filtered_df['genres'].apply(genre_match)]


# ==========================================
# 5. Main Dashboard Layout
# ==========================================
st.markdown('<div class="main-header"><h1>🎵 Spotify Data Explorer</h1><p>Interactive insights into artists, genres, and popularity</p></div>', unsafe_allow_html=True)

# Top Metrics
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Artists", len(filtered_df))
col_m2.metric("Avg Popularity", round(filtered_df['popularity'].mean(), 1) if not filtered_df.empty else 0)
col_m3.metric("Total Followers", f"{filtered_df['followers'].sum():,.0f}")
col_m4.metric("Total Monthly Listeners", f"{filtered_df['monthly_listeners'].sum():,.0f}")

st.markdown("<br>", unsafe_allow_html=True)

if filtered_df.empty:
    st.warning("⚠️ No data matches the selected filters. Please adjust your slicers.")
else:
    # ------------------------------------------
    # Chart 1: Scatter Plot (Popularity vs Listeners)
    # ------------------------------------------
    st.markdown("### 🌟 Artist Reach vs Popularity")
    fig1 = px.scatter(
        filtered_df, 
        x='monthly_listeners', 
        y='popularity', 
        size='followers', 
        color='names' if len(filtered_df) <= 20 else None,
        hover_name='names',
        hover_data=['genres', 'last_release'],
        title="Popularity vs Monthly Listeners (Bubble size = Followers)",
        labels={'monthly_listeners': 'Monthly Listeners', 'popularity': 'Spotify Popularity'},
        template="plotly_white"
    )
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

    # ------------------------------------------
    # Two-Column Layout for Charts 2 & 3
    # ------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        # Chart 2: Top 10 Artists by Followers (Bar Chart)
        st.markdown("### 🏆 Top Artists by Followers")
        top_artists = filtered_df.nlargest(10, 'followers')
        fig2 = px.bar(
            top_artists, 
            x='names', 
            y='followers', 
            color='popularity',
            text='followers',
            title="Top 10 Artists by Followers in Selection",
            labels={'names': 'Artist', 'followers': 'Followers'},
            color_continuous_scale="Viridis",
            template="plotly_white"
        )
        fig2.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig2.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # Chart 3: Distribution of Last Release Years (Histogram)
        st.markdown("### 📅 Activity based on Last Release")
        fig3 = px.histogram(
            filtered_df, 
            x='last_release',
            nbins=len(filtered_df['last_release'].unique()) or 10,
            title="Count of Artists by their Last Release Year",
            labels={'last_release': 'Last Release Year', 'count': 'Number of Artists'},
            color_discrete_sequence=['#1DB954'],
            template="plotly_white"
        )
        fig3.update_layout(bargap=0.1)
        st.plotly_chart(fig3, use_container_width=True)

    # ------------------------------------------
    # Data Table View
    # ------------------------------------------
    st.markdown("### 📄 Raw Data View")
    st.dataframe(
        filtered_df[['names', 'genres', 'monthly_listeners', 'followers', 'popularity', 'last_release']],
        use_container_width=True,
        hide_index=True
    )