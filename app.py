import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# API сервера
API_BASE = "http://77.232.128.127:5000/api"

st.set_page_config(page_title="Basketball Analytics", layout="wide")
st.title("🏀 Basketball Analytics Dashboard")

# Получить лиги
@st.cache_data(ttl=3600)
def get_leagues():
    try:
        response = requests.get(f"{API_BASE}/leagues", timeout=10)
        return pd.DataFrame(response.json())
    except:
        st.error("Не удалось загрузить лиги")
        return pd.DataFrame()

# Получить игры
@st.cache_data(ttl=300)
def get_games(date):
    try:
        response = requests.get(f"{API_BASE}/games/{date}", timeout=10)
        return pd.DataFrame(response.json())
    except:
        return pd.DataFrame()

# Фильтры
leagues = get_leagues()
if leagues.empty:
    st.stop()

# Выбор даты
selected_date = st.sidebar.date_input(
    "Выберите дату",
    value=datetime.now(),
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2026, 12, 31)
)

date_str = selected_date.strftime('%Y-%m-%d')

# Получить игры
games_df = get_games(date_str)

if games_df.empty:
    st.info(f"Нет игр на {date_str}")
else:
    st.success(f"Найдено игр: {len(games_df)}")
    
    for idx, game in games_df.iterrows():
        with st.expander(f"{game['home_team_name']} vs {game['away_team_name']} - {game['league_name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**{game['home_team_name']}**")
                if game['status'] == 'FT':
                    st.markdown(f"### {game['home_score']}")
            
            with col2:
                st.markdown(f"**{game['away_team_name']}**")
                if game['status'] == 'FT':
                    st.markdown(f"### {game['away_score']}")
