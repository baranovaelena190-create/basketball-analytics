#!/usr/bin/env python3
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Настройки страницы
st.set_page_config(page_title="Basketball Analytics", layout="wide")

DB_PATH = "data/basketball.db"

# Функции для работы с базой данных
@st.cache_data(ttl=3600)
def get_leagues():
    """Получить список всех лиг"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT DISTINCT id, name FROM leagues ORDER BY name", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def get_games_by_date(date_str, league_id=None):
    """Получить матчи на определенную дату"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            g.id,
            g.date,
            g.status,
            l.name as league_name,
            ht.name as home_team,
            ht.id as home_team_id,
            at.name as away_team,
            at.id as away_team_id,
            g.season
        FROM games g
        JOIN leagues l ON g.league_id = l.id
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE DATE(g.date) = ?
    """
    
    params = [date_str]
    
    if league_id and league_id != "Все лиги":
        query += " AND g.league_id = ?"
        params.append(league_id)
    
    query += " ORDER BY g.date"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def calculate_team_season_stats(team_id, season, is_home=None):
    """Статистика команды за сезон"""
    conn = sqlite3.connect(DB_PATH)
    
    home_away_filter = ""
    if is_home is True:
        home_away_filter = "AND g.home_team_id = ?"
    elif is_home is False:
        home_away_filter = "AND g.away_team_id = ?"
    
    query = f"""
        SELECT 
            COUNT(*) as games_played,
            AVG(CASE 
                WHEN g.home_team_id = ? THEN g.home_score 
                ELSE g.away_score 
            END) as avg_points,
            AVG(CASE 
                WHEN g.home_team_id = ? THEN g.away_score 
                ELSE g.home_score 
            END) as avg_points_against,
            SUM(CASE 
                WHEN (g.home_team_id = ? AND g.home_score > g.away_score) 
                OR (g.away_team_id = ? AND g.away_score > g.home_score) 
                THEN 1 ELSE 0 
            END) as wins
        FROM games g
        WHERE (g.home_team_id = ? OR g.away_team_id = ?)
        AND g.season = ?
        AND g.status = 'FT'
        {home_away_filter}
    """
    
    params = [team_id, team_id, team_id, team_id, team_id, team_id, season]
    if is_home is not None:
        params.append(team_id)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if len(df) > 0 and df['games_played'].iloc[0] > 0:
        row = df.iloc[0]
        return {
            'games': int(row['games_played']),
            'avg_points': round(row['avg_points'], 1) if row['avg_points'] else 0,
            'avg_against': round(row['avg_points_against'], 1) if row['avg_points_against'] else 0,
            'wins': int(row['wins']),
            'win_pct': round(row['wins'] / row['games_played'] * 100, 1) if row['games_played'] > 0 else 0
        }
    return None


def get_last_n_games(team_id, season, n=5, home_away=None):
    """Получить последние N матчей команды"""
    conn = sqlite3.connect(DB_PATH)
    
    home_away_filter = ""
    if home_away == "home":
        home_away_filter = "AND g.home_team_id = ?"
    elif home_away == "away":
        home_away_filter = "AND g.away_team_id = ?"
    
    query = f"""
        SELECT 
            g.id,
            g.date,
            g.home_team_id,
            g.away_team_id,
            ht.name as home_team,
            at.name as away_team,
            g.home_score,
            g.away_score,
            CASE WHEN g.home_team_id = ? THEN 'H' ELSE 'A' END as venue
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE (g.home_team_id = ? OR g.away_team_id = ?)
        AND g.season = ?
        AND g.status = 'FT'
        {home_away_filter}
        ORDER BY g.date DESC
        LIMIT ?
    """
    
    params = [team_id, team_id, team_id, season]
    if home_away:
        params.append(team_id)
    params.append(n)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def calculate_last_n_stats(team_id, season, n=5):
    """Статистика за последние N матчей с четвертями"""
    games = get_last_n_games(team_id, season, n)
    
    if len(games) == 0:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    
    stats = {
        'avg_points': 0,
        'avg_total': 0,
        'avg_q1': 0, 'avg_q2': 0, 'avg_q3': 0, 'avg_q4': 0,
        'avg_1h': 0, 'avg_2h': 0,
        'form': []
    }
    
    for _, game in games.iterrows():
        is_home = game['home_team_id'] == team_id
        team_score = game['home_score'] if is_home else game['away_score']
        opp_score = game['away_score'] if is_home else game['home_score']
        
        stats['avg_points'] += team_score
        stats['avg_total'] += team_score + opp_score
        stats['form'].append('W' if team_score > opp_score else 'L')
        
        # Получаем счет по четвертям
        quarters = pd.read_sql_query(
            "SELECT quarter_num, home_score, away_score FROM quarters WHERE game_id = ? ORDER BY quarter_num",
            conn, params=[game['id']]
        )
        
        for _, q in quarters.iterrows():
            q_score = q['home_score'] if is_home else q['away_score']
            stats[f'avg_q{q["quarter_num"]}'] += q_score
    
    conn.close()
    
    n_games = len(games)
    stats['avg_points'] = round(stats['avg_points'] / n_games, 1)
    stats['avg_total'] = round(stats['avg_total'] / n_games, 1)
    stats['avg_q1'] = round(stats['avg_q1'] / n_games, 1)
    stats['avg_q2'] = round(stats['avg_q2'] / n_games, 1)
    stats['avg_q3'] = round(stats['avg_q3'] / n_games, 1)
    stats['avg_q4'] = round(stats['avg_q4'] / n_games, 1)
    stats['avg_1h'] = round((stats['avg_q1'] * n_games + stats['avg_q2'] * n_games) / n_games, 1)
    stats['avg_2h'] = round((stats['avg_q3'] * n_games + stats['avg_q4'] * n_games) / n_games, 1)
    stats['form'] = '-'.join(stats['form'][:5])
    
    return stats

def get_h2h_stats(team1_id, team2_id, season):
    """Статистика личных встреч"""
    conn = sqlite3.connect(DB_PATH)
    
    games = pd.read_sql_query("""
        SELECT g.id, g.date, g.home_team_id, g.away_team_id, 
               g.home_score, g.away_score
        FROM games g
        WHERE ((g.home_team_id = ? AND g.away_team_id = ?) 
           OR (g.home_team_id = ? AND g.away_team_id = ?))
        AND g.season = ?
        AND g.status = 'FT'
        ORDER BY g.date DESC
    """, conn, params=[team1_id, team2_id, team2_id, team1_id, season])
    
    if len(games) == 0:
        conn.close()
        return None
    
    stats = {
        'count': len(games),
        'avg_total': 0,
        'avg_q1': 0, 'avg_q2': 0, 'avg_q3': 0, 'avg_q4': 0,
        'avg_1h': 0, 'avg_2h': 0
    }
    
    for _, game in games.iterrows():
        stats['avg_total'] += game['home_score'] + game['away_score']
        
        quarters = pd.read_sql_query(
            "SELECT quarter_num, home_score, away_score FROM quarters WHERE game_id = ?",
            conn, params=[game['id']]
        )
        
        for _, q in quarters.iterrows():
            stats[f'avg_q{q["quarter_num"]}'] += q['home_score'] + q['away_score']
    
    conn.close()
    
    n = len(games)
    stats['avg_total'] = round(stats['avg_total'] / n, 1)
    stats['avg_q1'] = round(stats['avg_q1'] / n, 1)
    stats['avg_q2'] = round(stats['avg_q2'] / n, 1)
    stats['avg_q3'] = round(stats['avg_q3'] / n, 1)
    stats['avg_q4'] = round(stats['avg_q4'] / n, 1)
    stats['avg_1h'] = round((stats['avg_q1'] * n + stats['avg_q2'] * n) / n, 1)
    stats['avg_2h'] = round((stats['avg_q3'] * n + stats['avg_q4'] * n) / n, 1)
    
    return stats

def days_since_last_game(team_id, current_date, season):
    """Количество дней с последнего матча"""
    conn = sqlite3.connect(DB_PATH)
    
    last_game = pd.read_sql_query("""
        SELECT MAX(date) as last_date
        FROM games
        WHERE (home_team_id = ? OR away_team_id = ?)
        AND date < ?
        AND season = ?
        AND status = 'FT'
    """, conn, params=[team_id, team_id, current_date, season])
    
    conn.close()
    
    if len(last_game) > 0 and last_game['last_date'].iloc[0]:
        last_date = datetime.fromisoformat(last_game['last_date'].iloc[0].replace('Z', '+00:00'))
        current = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
        return (current - last_date).days
    return None


# Интерфейс приложения
st.title("🏀 Basketball Analytics Dashboard")

# Боковая панель с фильтрами
st.sidebar.header("Фильтры")

# Выбор даты
selected_date = st.sidebar.date_input(
    "Выберите дату",
    value=datetime.now(),
    format="DD.MM.YYYY"
)

# Выбор лиги
leagues = get_leagues()
league_options = ["Все лиги"] + leagues['name'].tolist()
selected_league = st.sidebar.selectbox("Выберите лигу", league_options)

# Получаем ID выбранной лиги
league_id = None
if selected_league != "Все лиги":
    league_id = leagues[leagues['name'] == selected_league]['id'].iloc[0]

# Получаем матчи на выбранную дату
date_str = selected_date.strftime('%Y-%m-%d')
games = get_games_by_date(date_str, league_id)

st.header(f"Матчи на {selected_date.strftime('%d.%m.%Y')}")

if len(games) == 0:
    st.warning("На выбранную дату нет матчей")
else:
    st.write(f"Найдено матчей: {len(games)}")
    
    # Отображаем каждый матч
    for idx, game in games.iterrows():
        with st.expander(
            f"🏀 {game['league_name']} | {game['home_team']} vs {game['away_team']} | {game['date'][11:16]}"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"🏠 {game['home_team']}")
                
                # Статистика за сезон дома
                season_home = calculate_team_season_stats(game['home_team_id'], game['season'], is_home=True)
                if season_home:
                    st.write(f"**Сезон (дома):** {season_home['games']} игр, {season_home['wins']}П, {season_home['win_pct']}%")
                    st.write(f"Ср. очки: {season_home['avg_points']} | Пропущено: {season_home['avg_against']}")
                
                # Дни отдыха
                days_rest = days_since_last_game(game['home_team_id'], game['date'], game['season'])
                if days_rest:
                    st.write(f"🛌 Дней отдыха: {days_rest}")
                
                # Последние 5 матчей
                st.write("---")
                st.write("**Последние 5 матчей:**")
                last5 = calculate_last_n_stats(game['home_team_id'], game['season'], 5)
                if last5:
                    st.write(f"Форма: {last5['form']}")
                    st.write(f"Ср. очки: {last5['avg_points']} | Ср. тотал: {last5['avg_total']}")
                    st.write(f"Четверти: Q1={last5['avg_q1']}, Q2={last5['avg_q2']}, Q3={last5['avg_q3']}, Q4={last5['avg_q4']}")
                    st.write(f"Половины: 1H={last5['avg_1h']}, 2H={last5['avg_2h']}")
                
                # Последние 10 матчей
                st.write("---")
                st.write("**Последние 10 матчей:**")
                last10 = calculate_last_n_stats(game['home_team_id'], game['season'], 10)
                if last10:
                    st.write(f"Ср. очки: {last10['avg_points']} | Ср. тотал: {last10['avg_total']}")
                    st.write(f"Четверти: Q1={last10['avg_q1']}, Q2={last10['avg_q2']}, Q3={last10['avg_q3']}, Q4={last10['avg_q4']}")
                    st.write(f"Половины: 1H={last10['avg_1h']}, 2H={last10['avg_2h']}")
            
            with col2:
                st.subheader(f"✈️ {game['away_team']}")
                
                # Статистика за сезон в гостях
                season_away = calculate_team_season_stats(game['away_team_id'], game['season'], is_home=False)
                if season_away:
                    st.write(f"**Сезон (в гостях):** {season_away['games']} игр, {season_away['wins']}П, {season_away['win_pct']}%")
                    st.write(f"Ср. очки: {season_away['avg_points']} | Пропущено: {season_away['avg_against']}")
                
                # Дни отдыха
                days_rest = days_since_last_game(game['away_team_id'], game['date'], game['season'])
                if days_rest:
                    st.write(f"🛌 Дней отдыха: {days_rest}")
                
                # Последние 5 матчей
                st.write("---")
                st.write("**Последние 5 матчей:**")
                last5 = calculate_last_n_stats(game['away_team_id'], game['season'], 5)
                if last5:
                    st.write(f"Форма: {last5['form']}")
                    st.write(f"Ср. очки: {last5['avg_points']} | Ср. тотал: {last5['avg_total']}")
                    st.write(f"Четверти: Q1={last5['avg_q1']}, Q2={last5['avg_q2']}, Q3={last5['avg_q3']}, Q4={last5['avg_q4']}")
                    st.write(f"Половины: 1H={last5['avg_1h']}, 2H={last5['avg_2h']}")
                
                # Последние 10 матчей
                st.write("---")
                st.write("**Последние 10 матчей:**")
                last10 = calculate_last_n_stats(game['away_team_id'], game['season'], 10)
                if last10:
                    st.write(f"Ср. очки: {last10['avg_points']} | Ср. тотал: {last10['avg_total']}")
                    st.write(f"Четверти: Q1={last10['avg_q1']}, Q2={last10['avg_q2']}, Q3={last10['avg_q3']}, Q4={last10['avg_q4']}")
                    st.write(f"Половины: 1H={last10['avg_1h']}, 2H={last10['avg_2h']}")
            
            # Личные встречи
            st.write("---")
            st.subheader("🤝 Личные встречи (текущий сезон)")
            h2h = get_h2h_stats(game['home_team_id'], game['away_team_id'], game['season'])
            if h2h:
                st.write(f"Встреч: {h2h['count']}")
                st.write(f"Ср. тотал: {h2h['avg_total']}")
                st.write(f"Четверти: Q1={h2h['avg_q1']}, Q2={h2h['avg_q2']}, Q3={h2h['avg_q3']}, Q4={h2h['avg_q4']}")
                st.write(f"Половины: 1H={h2h['avg_1h']}, 2H={h2h['avg_2h']}")
            else:
                st.write("Личных встреч в текущем сезоне не было")

