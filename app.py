import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# Конфигурация API
API_BASE = "http://77.232.128.127:5000/api"

# Настройка страницы
st.set_page_config(page_title="Панель аналитики баскетбола", layout="wide", page_icon="🏀")

# Заголовок
st.title("🏀 Панель аналитики баскетбола")

# Функции для работы с API
@st.cache_data(ttl=3600)
def get_leagues():
    """Получить список лиг"""
    try:
        response = requests.get(f"{API_BASE}/leagues", timeout=10)
        return pd.DataFrame(response.json())
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_games(date):
    """Получить игры на дату"""
    try:
        response = requests.get(f"{API_BASE}/games/{date}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300)
def get_team_averages(team_id, limit):
    """Получить средние показатели команды"""
    try:
        response = requests.get(f"{API_BASE}/team_averages/{team_id}/{limit}", timeout=10)
        data = response.json()
        return data if data.get('games_count', 0) > 0 else None
    except:
        return None

@st.cache_data(ttl=300)
def get_last_games(team_id, limit):
    """Получить последние матчи команды"""
    try:
        response = requests.get(f"{API_BASE}/last_games/{team_id}/{limit}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300)
def get_h2h(team1_id, team2_id, season):
    """Получить личные встречи"""
    try:
        response = requests.get(f"{API_BASE}/h2h/{team1_id}/{team2_id}/{season}", timeout=10)
        return response.json()
    except:
        return []

@st.cache_data(ttl=300)
def get_rest_days(team_id):
    """Получить дни отдыха команды"""
    try:
        response = requests.get(f"{API_BASE}/team_rest_days/{team_id}", timeout=10)
        return response.json()
    except:
        return {'rest_days': None}

# Боковая панель с фильтрами
st.sidebar.header("Фильтры")

# Выбор даты
selected_date = st.sidebar.date_input(
    "Выберите дату",
    value=datetime.now(),
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2026, 12, 31)
)
date_str = selected_date.strftime('%Y-%m-%d')

# Выбор лиги
leagues = get_leagues()
if not leagues.empty:
    league_options = ['Все лиги'] + leagues['name'].tolist()
    selected_league = st.sidebar.selectbox("Выберите лигу", league_options)
else:
    selected_league = 'Все лиги'

# Получить игры
games = get_games(date_str)

if not games:
    st.info(f"📅 Нет игр на {date_str}")
    st.stop()

# Фильтр по лиге
if selected_league != 'Все лиги':
    games = [g for g in games if g['league_name'] == selected_league]

st.success(f"Найдено игр: {len(games)}")

# Отображение игр
for game in games:
    home_id = game['home_team_id']
    away_id = game['away_team_id']
    season = game['season']
    
    # Заголовок матча
    match_title = f"**{game['home_team_name']}** vs **{game['away_team_name']}** — {game['league_name']}"
    
    with st.expander(match_title, expanded=False):
        # Информация о матче
        st.markdown(f"**Дата:** {game['date'][:16]} | **Статус:** {game['status']}")
        
        # Получаем статистику для обеих команд
        with st.spinner('Загрузка статистики...'):
            home_avg_5 = get_team_averages(home_id, 5)
            away_avg_5 = get_team_averages(away_id, 5)
            home_avg_10 = get_team_averages(home_id, 10)
            away_avg_10 = get_team_averages(away_id, 10)
            home_rest = get_rest_days(home_id)
            away_rest = get_rest_days(away_id)
        
        # Основная статистика в таблице
        st.markdown("### 📊 Основная статистика")
        
        # Создаём таблицу со статистикой
        stats_data = {
            'Команда': [game['home_team_name'], game['away_team_name']],
            'Дней отдыха': [
                home_rest.get('rest_days', '-') if home_rest.get('rest_days') is not None else '-',
                away_rest.get('rest_days', '-') if away_rest.get('rest_days') is not None else '-'
            ]
        }
        
        # Добавляем средние за последние 5 игр
        if home_avg_5 is not None and away_avg_5 is not None:
            stats_data['Ср. очки (5 игр)'] = [
                f"{home_avg_5['avg_score']:.1f}",
                f"{away_avg_5['avg_score']:.1f}"
            ]
            stats_data['Q1 (5)'] = [
                f"{home_avg_5['quarters'].get('q1', 0):.1f}",
                f"{away_avg_5['quarters'].get('q1', 0):.1f}"
            ]
            stats_data['Q2 (5)'] = [
                f"{home_avg_5['quarters'].get('q2', 0):.1f}",
                f"{away_avg_5['quarters'].get('q2', 0):.1f}"
            ]
            stats_data['Q3 (5)'] = [
                f"{home_avg_5['quarters'].get('q3', 0):.1f}",
                f"{away_avg_5['quarters'].get('q3', 0):.1f}"
            ]
            stats_data['Q4 (5)'] = [
                f"{home_avg_5['quarters'].get('q4', 0):.1f}",
                f"{away_avg_5['quarters'].get('q4', 0):.1f}"
            ]
            stats_data['H1 (5)'] = [
                f"{home_avg_5['halves'].get('h1', 0):.1f}",
                f"{away_avg_5['halves'].get('h1', 0):.1f}"
            ]
            stats_data['H2 (5)'] = [
                f"{home_avg_5['halves'].get('h2', 0):.1f}",
                f"{away_avg_5['halves'].get('h2', 0):.1f}"
            ]
        
        # Добавляем средние за последние 10 игр
        if home_avg_10 is not None and away_avg_10 is not None:
            stats_data['Ср. очки (10 игр)'] = [
                f"{home_avg_10['avg_score']:.1f}",
                f"{away_avg_10['avg_score']:.1f}"
            ]
            stats_data['Q1 (10)'] = [
                f"{home_avg_10['quarters'].get('q1', 0):.1f}",
                f"{away_avg_10['quarters'].get('q1', 0):.1f}"
            ]
            stats_data['Q2 (10)'] = [
                f"{home_avg_10['quarters'].get('q2', 0):.1f}",
                f"{away_avg_10['quarters'].get('q2', 0):.1f}"
            ]
            stats_data['Q3 (10)'] = [
                f"{home_avg_10['quarters'].get('q3', 0):.1f}",
                f"{away_avg_10['quarters'].get('q3', 0):.1f}"
            ]
            stats_data['Q4 (10)'] = [
                f"{home_avg_10['quarters'].get('q4', 0):.1f}",
                f"{away_avg_10['quarters'].get('q4', 0):.1f}"
            ]
            stats_data['H1 (10)'] = [
                f"{home_avg_10['halves'].get('h1', 0):.1f}",
                f"{away_avg_10['halves'].get('h1', 0):.1f}"
            ]
            stats_data['H2 (10)'] = [
                f"{home_avg_10['halves'].get('h2', 0):.1f}",
                f"{away_avg_10['halves'].get('h2', 0):.1f}"
            ]
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Детальная статистика
        st.markdown("---")
        st.markdown("### 📈 Детальная статистика")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### {game['home_team_name']}")
            
            # Последние 5 матчей
            st.markdown("**Последние 5 матчей:**")
            home_last_5 = get_last_games(home_id, 5)
            
            if home_last_5:
                last_games_data = []
                for lg in home_last_5:
                    quarters_str = ""
                    if lg.get('quarters'):
                        q_scores = [q.get('home_score' if lg['is_home'] else 'away_score', 0) for q in lg['quarters'][:4]]
                        quarters_str = f"Q: {'-'.join(map(str, q_scores))}"
                    
                    last_games_data.append({
                        'Дата': lg['date'][:10],
                        'Соперник': lg['opponent_name'],
                        'Место': lg['location'],
                        'Счёт': f"{lg['team_score']}-{lg['opponent_score']}",
                        'Рез-т': lg['result'] or '-',
                        'Четверти': quarters_str
                    })
                
                st.dataframe(pd.DataFrame(last_games_data), use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных")
        
        with col2:
            st.markdown(f"#### {game['away_team_name']}")
            
            # Последние 5 матчей
            st.markdown("**Последние 5 матчей:**")
            away_last_5 = get_last_games(away_id, 5)
            
            if away_last_5:
                last_games_data = []
                for lg in away_last_5:
                    quarters_str = ""
                    if lg.get('quarters'):
                        q_scores = [q.get('home_score' if lg['is_home'] else 'away_score', 0) for q in lg['quarters'][:4]]
                        quarters_str = f"Q: {'-'.join(map(str, q_scores))}"
                    
                    last_games_data.append({
                        'Дата': lg['date'][:10],
                        'Соперник': lg['opponent_name'],
                        'Место': lg['location'],
                        'Счёт': f"{lg['team_score']}-{lg['opponent_score']}",
                        'Рез-т': lg['result'] or '-',
                        'Четверти': quarters_str
                    })
                
                st.dataframe(pd.DataFrame(last_games_data), use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных")
        
        # Личные встречи (H2H)
        st.markdown("---")
        st.markdown("### 🔄 Личные встречи (H2H)")
        
        h2h_games = get_h2h(home_id, away_id, season)
        
        if h2h_games:
            h2h_data = []
            for h2h in h2h_games:
                quarters_str = ""
                if h2h.get('quarters'):
                    home_q = [q.get('home_score', 0) for q in h2h['quarters'][:4]]
                    away_q = [q.get('away_score', 0) for q in h2h['quarters'][:4]]
                    quarters_str = f"H: {'-'.join(map(str, home_q))} | A: {'-'.join(map(str, away_q))}"
                
                h2h_data.append({
                    'Дата': h2h['date'][:10],
                    'Хозяева': h2h['home_team_name'],
                    'Гости': h2h['away_team_name'],
                    'Счёт': f"{h2h['home_score']}-{h2h['away_score']}" if h2h.get('home_score') else '-',
                    'Четверти': quarters_str
                })
            
            st.dataframe(pd.DataFrame(h2h_data), use_container_width=True, hide_index=True)
            
            # Средние по H2H
            if len(h2h_games) > 0:
                st.markdown("**Средние показатели по личным встречам:**")
                
                h2h_home_scores = []
                h2h_away_scores = []
                h2h_quarters = {'q1_home': [], 'q2_home': [], 'q3_home': [], 'q4_home': [],
                               'q1_away': [], 'q2_away': [], 'q3_away': [], 'q4_away': []}
                
                for h2h in h2h_games:
                    if h2h.get('home_score') and h2h.get('away_score'):
                        h2h_home_scores.append(h2h['home_score'])
                        h2h_away_scores.append(h2h['away_score'])
                        
                        if h2h.get('quarters'):
                            for i, q in enumerate(h2h['quarters'][:4], 1):
                                h2h_quarters[f'q{i}_home'].append(q.get('home_score', 0))
                                h2h_quarters[f'q{i}_away'].append(q.get('away_score', 0))
                
                if h2h_home_scores:
                    avg_h2h_home = sum(h2h_home_scores) / len(h2h_home_scores)
                    avg_h2h_away = sum(h2h_away_scores) / len(h2h_away_scores)
                    
                    h2h_avg_data = {
                        'Команда': [game['home_team_name'], game['away_team_name']],
                        'Ср. очки': [f"{avg_h2h_home:.1f}", f"{avg_h2h_away:.1f}"]
                    }
                    
                    # Добавляем средние по четвертям
                    for i in range(1, 5):
                        if h2h_quarters[f'q{i}_home']:
                            avg_q_home = sum(h2h_quarters[f'q{i}_home']) / len(h2h_quarters[f'q{i}_home'])
                            avg_q_away = sum(h2h_quarters[f'q{i}_away']) / len(h2h_quarters[f'q{i}_away'])
                            h2h_avg_data[f'Q{i}'] = [f"{avg_q_home:.1f}", f"{avg_q_away:.1f}"]
                    
                    st.dataframe(pd.DataFrame(h2h_avg_data), use_container_width=True, hide_index=True)
        else:
            st.info(f"Нет личных встреч в сезоне {season}")

# Футер
st.markdown("---")
st.markdown("*Данные обновляются автоматически каждые 60 секунд*")
