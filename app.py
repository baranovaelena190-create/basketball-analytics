import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

API_BASE = "http://77.232.128.127:5000/api"

st.set_page_config(page_title="Панель аналитики баскетбола", layout="wide", page_icon="🏀")
st.title("🏀 Панель аналитики баскетбола")

@st.cache_data(ttl=3600, show_spinner=False)
def get_leagues():
    try:
        response = requests.get(f"{API_BASE}/leagues", timeout=10)
        return pd.DataFrame(response.json())
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def get_games(date):
    try:
        response = requests.get(f"{API_BASE}/games/{date}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def get_team_averages(team_id, limit):
    try:
        response = requests.get(f"{API_BASE}/team_averages/{team_id}/{limit}", timeout=10)
        data = response.json()
        return data if data.get('games_count', 0) > 0 else None
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_last_games(team_id, limit):
    try:
        response = requests.get(f"{API_BASE}/last_games/{team_id}/{limit}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def get_h2h(team1_id, team2_id, season):
    try:
        response = requests.get(f"{API_BASE}/h2h/{team1_id}/{team2_id}/{season}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def get_h2h_averages(team1_id, team2_id, season):
    try:
        response = requests.get(f"{API_BASE}/h2h_averages/{team1_id}/{team2_id}/{season}", timeout=10)
        return response.json()
    except:
        return {}

@st.cache_data(ttl=300, show_spinner=False)
def get_rest_days(team_id):
    try:
        response = requests.get(f"{API_BASE}/team_rest_days/{team_id}", timeout=10)
        return response.json()
    except:
        return {'rest_days': None}

st.sidebar.header("Фильтры")

selected_date = st.sidebar.date_input(
    "Выберите дату",
    value=datetime.now(),
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2026, 12, 31)
)
date_str = selected_date.strftime('%Y-%m-%d')

leagues = get_leagues()
if not leagues.empty:
    league_options = ['Все лиги'] + leagues['name'].tolist()
    selected_league = st.sidebar.selectbox("Выберите лигу", league_options)
else:
    selected_league = 'Все лиги'

games = get_games(date_str)

if not games:
    st.info(f"📅 Нет игр на {date_str}")
    st.stop()

if selected_league != 'Все лиги':
    games = [g for g in games if g['league_name'] == selected_league]

st.success(f"📊 Найдено игр: **{len(games)}**")

for game in games:
    home_id = game['home_team_id']
    away_id = game['away_team_id']
    season = game['season']
    
    match_title = f"**{game['home_team_name']}** vs **{game['away_team_name']}** — {game['league_name']}"
    
    with st.expander(match_title, expanded=False):
        st.markdown(f"**🕐 Дата:** {game['date'][:16]} | **📍 Статус:** {game['status']}")
        
        home_avg_5 = get_team_averages(home_id, 5)
        away_avg_5 = get_team_averages(away_id, 5)
        home_avg_10 = get_team_averages(home_id, 10)
        away_avg_10 = get_team_averages(away_id, 10)
        home_rest = get_rest_days(home_id)
        away_rest = get_rest_days(away_id)
        
        st.markdown("### 📊 Средние показатели")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown(f"#### {game['home_team_name']} (Хозяева)")
            if home_avg_5 and home_avg_10:
                home_data = {
                    'Показатель': ['Дней отдыха', 'Ср. очки (5)', 'Ср. очки (10)', 
                                   'Q1 (5)', 'Q2 (5)', 'H1 (5)', 
                                   'Q3 (5)', 'Q4 (5)', 'H2 (5)'],
                    'Значение': [
                        home_rest.get('rest_days', '-') if home_rest.get('rest_days') is not None else '-',
                        f"{home_avg_5['avg_score']:.1f}",
                        f"{home_avg_10['avg_score']:.1f}",
                        f"{home_avg_5['quarters'].get('q1', 0):.1f}",
                        f"{home_avg_5['quarters'].get('q2', 0):.1f}",
                        f"{home_avg_5['halves'].get('h1', 0):.1f}",
                        f"{home_avg_5['quarters'].get('q3', 0):.1f}",
                        f"{home_avg_5['quarters'].get('q4', 0):.1f}",
                        f"{home_avg_5['halves'].get('h2', 0):.1f}"
                    ]
                }
                st.dataframe(pd.DataFrame(home_data), use_container_width=True, hide_index=True)
        
        with col_right:
            st.markdown(f"#### {game['away_team_name']} (Гости)")
            if away_avg_5 and away_avg_10:
                away_data = {
                    'Показатель': ['Дней отдыха', 'Ср. очки (5)', 'Ср. очки (10)', 
                                   'Q1 (5)', 'Q2 (5)', 'H1 (5)', 
                                   'Q3 (5)', 'Q4 (5)', 'H2 (5)'],
                    'Значение': [
                        away_rest.get('rest_days', '-') if away_rest.get('rest_days') is not None else '-',
                        f"{away_avg_5['avg_score']:.1f}",
                        f"{away_avg_10['avg_score']:.1f}",
                        f"{away_avg_5['quarters'].get('q1', 0):.1f}",
                        f"{away_avg_5['quarters'].get('q2', 0):.1f}",
                        f"{away_avg_5['halves'].get('h1', 0):.1f}",
                        f"{away_avg_5['quarters'].get('q3', 0):.1f}",
                        f"{away_avg_5['quarters'].get('q4', 0):.1f}",
                        f"{away_avg_5['halves'].get('h2', 0):.1f}"
                    ]
                }
                st.dataframe(pd.DataFrame(away_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🔄 Личные встречи (H2H)")
        
        h2h_games = get_h2h(home_id, away_id, season)
        
        if h2h_games:
            h2h_data = []
            for h2h in h2h_games:
                quarters_str = ""
                if h2h.get('quarters'):
                    home_q = [str(q.get('home_score', 0)) for q in h2h['quarters'][:4]]
                    away_q = [str(q.get('away_score', 0)) for q in h2h['quarters'][:4]]
                    quarters_str = f"H: {'-'.join(home_q)} | A: {'-'.join(away_q)}"
                
                h2h_data.append({
                    'Дата': h2h['date'][:10],
                    'Хозяева': h2h['home_team_name'],
                    'Гости': h2h['away_team_name'],
                    'Счёт': f"{h2h['home_score']}-{h2h['away_score']}" if h2h.get('home_score') else '-',
                    'Четверти': quarters_str
                })
            
            st.dataframe(pd.DataFrame(h2h_data), use_container_width=True, hide_index=True)
            
            h2h_avg = get_h2h_averages(home_id, away_id, season)
            
            if h2h_avg and h2h_avg.get('games_count', 0) > 0:
                st.markdown(f"**📈 Средние по {h2h_avg['games_count']} личным встречам:**")
                
                h2h_avg_data = {
                    'Команда': [game['home_team_name'], game['away_team_name']],
                    'Ср. очки': [f"{h2h_avg['team1_avg']:.1f}", f"{h2h_avg['team2_avg']:.1f}"],
                    'Q1': [
                        f"{h2h_avg['team1_quarters'].get('q1', 0):.1f}",
                        f"{h2h_avg['team2_quarters'].get('q1', 0):.1f}"
                    ],
                    'Q2': [
                        f"{h2h_avg['team1_quarters'].get('q2', 0):.1f}",
                        f"{h2h_avg['team2_quarters'].get('q2', 0):.1f}"
                    ],
                    'Q3': [
                        f"{h2h_avg['team1_quarters'].get('q3', 0):.1f}",
                        f"{h2h_avg['team2_quarters'].get('q3', 0):.1f}"
                    ],
                    'Q4': [
                        f"{h2h_avg['team1_quarters'].get('q4', 0):.1f}",
                        f"{h2h_avg['team2_quarters'].get('q4', 0):.1f}"
                    ]
                }
                
                st.dataframe(pd.DataFrame(h2h_avg_data), use_container_width=True, hide_index=True)
        else:
            st.info(f"Нет личных встреч в сезоне {season}")
        
        st.markdown("---")
        st.markdown("### 📈 Последние матчи")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### {game['home_team_name']}")
            home_last_5 = get_last_games(home_id, 5)
            
            if home_last_5:
                last_games_data = []
                for lg in home_last_5:
                    if lg['home_team_id'] == home_id:
                        team_score = lg['home_score']
                        opp_score = lg['away_score']
                        is_home_game = True
                    else:
                        team_score = lg['away_score']
                        opp_score = lg['home_score']
                        is_home_game = False
                    
                    quarters_str = ""
                    if lg.get('quarters'):
                        q_scores = []
                        for q in lg['quarters'][:4]:
                            if is_home_game:
                                q_scores.append(str(q.get('home_score', 0)))
                            else:
                                q_scores.append(str(q.get('away_score', 0)))
                        quarters_str = f"{'-'.join(q_scores)}"
                    
                    last_games_data.append({
                        'Дата': lg['date'][:10],
                        'Соперник': lg['opponent_name'],
                        'Место': lg['location'],
                        'Счёт': f"{team_score}-{opp_score}",
                        'Рез.': lg['result'] or '-',
                        'Четверти': quarters_str
                    })
                
                st.dataframe(pd.DataFrame(last_games_data), use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных")
        
        with col2:
            st.markdown(f"#### {game['away_team_name']}")
            away_last_5 = get_last_games(away_id, 5)
            
            if away_last_5:
                last_games_data = []
                for lg in away_last_5:
                    if lg['home_team_id'] == away_id:
                        team_score = lg['home_score']
                        opp_score = lg['away_score']
                        is_home_game = True
                    else:
                        team_score = lg['away_score']
                        opp_score = lg['home_score']
                        is_home_game = False
                    
                    quarters_str = ""
                    if lg.get('quarters'):
                        q_scores = []
                        for q in lg['quarters'][:4]:
                            if is_home_game:
                                q_scores.append(str(q.get('home_score', 0)))
                            else:
                                q_scores.append(str(q.get('away_score', 0)))
                        quarters_str = f"{'-'.join(q_scores)}"
                    
                    last_games_data.append({
                        'Дата': lg['date'][:10],
                        'Соперник': lg['opponent_name'],
                        'Место': lg['location'],
                        'Счёт': f"{team_score}-{opp_score}",
                        'Рез.': lg['result'] or '-',
                        'Четверти': quarters_str
                    })
                
                st.dataframe(pd.DataFrame(last_games_data), use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных")

st.markdown("---")
st.markdown("*Данные обновляются автоматически каждые 60 секунд*")
