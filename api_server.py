from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DB_PATH = "/root/basketball_project/data/basketball.db"

def _db_query(query, params=()):
    """Выполнить SQL запрос и вернуть результат как список словарей"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    """Получить список всех лиг"""
    rows = _db_query("SELECT DISTINCT id, name FROM leagues ORDER BY name")
    return jsonify(rows)

@app.route('/api/games/<date>', methods=['GET'])
def get_games(date):
    """Получить игры на указанную дату"""
    query = """
    SELECT g.*, 
           l.name as league_name,
           t1.name as home_team_name, t1.logo as home_team_logo,
           t2.name as away_team_name, t2.logo as away_team_logo
    FROM games g
    JOIN leagues l ON g.league_id = l.id
    JOIN teams t1 ON g.home_team_id = t1.id
    JOIN teams t2 ON g.away_team_id = t2.id
    WHERE substr(g.date, 1, 10) = ?
    ORDER BY g.timestamp
    """
    rows = _db_query(query, (date,))
    return jsonify(rows)

@app.route('/api/quarters/<int:game_id>', methods=['GET'])
def get_quarters(game_id):
    """Получить счёт по четвертям для конкретного матча"""
    rows = _db_query("SELECT * FROM quarters WHERE game_id = ? ORDER BY quarter_num", (game_id,))
    return jsonify(rows)

@app.route('/api/last_games/<int:team_id>/<int:limit>', methods=['GET'])
def get_last_games(team_id, limit):
    """Получить последние N матчей команды"""
    query = """
    SELECT g.*,
           l.name as league_name,
           CASE 
               WHEN g.home_team_id = ? THEN t2.name
               ELSE t1.name
           END as opponent_name,
           CASE 
               WHEN g.home_team_id = ? THEN 'H'
               ELSE 'A'
           END as location,
           CASE
               WHEN g.home_team_id = ? AND g.home_score > g.away_score THEN 'W'
               WHEN g.away_team_id = ? AND g.away_score > g.home_score THEN 'W'
               WHEN g.status = 'FT' THEN 'L'
               ELSE NULL
           END as result
    FROM games g
    JOIN leagues l ON g.league_id = l.id
    JOIN teams t1 ON g.home_team_id = t1.id
    JOIN teams t2 ON g.away_team_id = t2.id
    WHERE (g.home_team_id = ? OR g.away_team_id = ?)
      AND g.status = 'FT'
    ORDER BY g.date DESC
    LIMIT ?
    """
    rows = _db_query(query, (team_id, team_id, team_id, team_id, team_id, team_id, limit))
    
    for row in rows:
        quarters = _db_query("SELECT * FROM quarters WHERE game_id = ? ORDER BY quarter_num", (row['id'],))
        row['quarters'] = quarters
    
    return jsonify(rows)

@app.route('/api/h2h/<int:team1_id>/<int:team2_id>/<season>', methods=['GET'])
def get_h2h(team1_id, team2_id, season):
    """Получить личные встречи двух команд за сезон"""
    query = """
    SELECT g.*,
           l.name as league_name,
           t1.name as home_team_name,
           t2.name as away_team_name
    FROM games g
    JOIN leagues l ON g.league_id = l.id
    JOIN teams t1 ON g.home_team_id = t1.id
    JOIN teams t2 ON g.away_team_id = t2.id
    WHERE ((g.home_team_id = ? AND g.away_team_id = ?)
           OR (g.home_team_id = ? AND g.away_team_id = ?))
      AND g.season = ?
      AND g.status = 'FT'
      AND g.home_score IS NOT NULL
      AND g.away_score IS NOT NULL
    ORDER BY g.date DESC
    """
    rows = _db_query(query, (team1_id, team2_id, team2_id, team1_id, season))
    
    for row in rows:
        quarters = _db_query("SELECT * FROM quarters WHERE game_id = ? ORDER BY quarter_num", (row['id'],))
        row['quarters'] = quarters
    
    return jsonify(rows)

@app.route('/api/team_averages/<int:team_id>/<int:limit>', methods=['GET'])
def get_team_averages(team_id, limit):
    """Получить средние показатели команды за последние N игр"""
    games_query = """
    SELECT g.*,
           CASE WHEN g.home_team_id = ? THEN g.home_score ELSE g.away_score END as team_score,
           CASE WHEN g.home_team_id = ? THEN g.away_score ELSE g.home_score END as opponent_score,
           CASE WHEN g.home_team_id = ? THEN 1 ELSE 0 END as is_home
    FROM games g
    WHERE (g.home_team_id = ? OR g.away_team_id = ?)
      AND g.status = 'FT'
      AND g.home_score IS NOT NULL
      AND g.away_score IS NOT NULL
    ORDER BY g.date DESC
    LIMIT ?
    """
    games = _db_query(games_query, (team_id, team_id, team_id, team_id, team_id, limit))
    
    if not games:
        return jsonify({
            'games_count': 0,
            'avg_score': 0,
            'avg_opponent_score': 0,
            'avg_total': 0,
            'quarters': {},
            'halves': {}
        })
    
    avg_score = sum(g['team_score'] for g in games) / len(games)
    avg_opponent = sum(g['opponent_score'] for g in games) / len(games)
    avg_total = avg_score + avg_opponent
    
    quarters_sum = {'q1': [], 'q2': [], 'q3': [], 'q4': []}
    
    for game in games:
        quarters = _db_query("SELECT * FROM quarters WHERE game_id = ? ORDER BY quarter_num", (game['id'],))
        
        if quarters:
            for q in quarters:
                quarter_num = q['quarter_num']
                if quarter_num <= 4:
                    if game['is_home']:
                        score = q['home_score'] or 0
                    else:
                        score = q['away_score'] or 0
                    
                    quarters_sum[f'q{quarter_num}'].append(score)
    
    quarters_avg = {}
    for q_key, scores in quarters_sum.items():
        if scores:
            quarters_avg[q_key] = round(sum(scores) / len(scores), 1)
        else:
            quarters_avg[q_key] = 0
    
    halves_avg = {}
    if quarters_avg.get('q1', 0) > 0 and quarters_avg.get('q2', 0) > 0:
        halves_avg['h1'] = round(quarters_avg['q1'] + quarters_avg['q2'], 1)
    else:
        halves_avg['h1'] = 0
        
    if quarters_avg.get('q3', 0) > 0 and quarters_avg.get('q4', 0) > 0:
        halves_avg['h2'] = round(quarters_avg['q3'] + quarters_avg['q4'], 1)
    else:
        halves_avg['h2'] = 0
    
    return jsonify({
        'games_count': len(games),
        'avg_score': round(avg_score, 1),
        'avg_opponent_score': round(avg_opponent, 1),
        'avg_total': round(avg_total, 1),
        'quarters': quarters_avg,
        'halves': halves_avg
    })

@app.route('/api/team_rest_days/<int:team_id>', methods=['GET'])
def get_team_rest_days(team_id):
    """Получить количество дней отдыха команды"""
    query = """
    SELECT MAX(date) as last_game_date
    FROM games
    WHERE (home_team_id = ? OR away_team_id = ?)
      AND status = 'FT'
    """
    result = _db_query(query, (team_id, team_id))
    
    if result and result[0]['last_game_date']:
        last_game = datetime.fromisoformat(result[0]['last_game_date'].replace('T', ' ').replace('+00:00', ''))
        today = datetime.now()
        rest_days = (today - last_game).days
        return jsonify({'rest_days': rest_days, 'last_game_date': result[0]['last_game_date']})
    
    return jsonify({'rest_days': None, 'last_game_date': None})

@app.route('/api/h2h_averages/<int:team1_id>/<int:team2_id>/<season>', methods=['GET'])
def get_h2h_averages(team1_id, team2_id, season):
    """Получить средние показатели по личным встречам"""
    query = """
    SELECT g.*
    FROM games g
    WHERE ((g.home_team_id = ? AND g.away_team_id = ?)
           OR (g.home_team_id = ? AND g.away_team_id = ?))
      AND g.season = ?
      AND g.status = 'FT'
      AND g.home_score IS NOT NULL
      AND g.away_score IS NOT NULL
    ORDER BY g.date DESC
    """
    games = _db_query(query, (team1_id, team2_id, team2_id, team1_id, season))
    
    if not games:
        return jsonify({
            'games_count': 0,
            'team1_avg': 0,
            'team2_avg': 0,
            'team1_quarters': {},
            'team2_quarters': {}
        })
    
    team1_scores = []
    team2_scores = []
    team1_quarters = {'q1': [], 'q2': [], 'q3': [], 'q4': []}
    team2_quarters = {'q1': [], 'q2': [], 'q3': [], 'q4': []}
    
    for game in games:
        if game['home_team_id'] == team1_id:
            team1_scores.append(game['home_score'])
            team2_scores.append(game['away_score'])
            team1_is_home = True
        else:
            team1_scores.append(game['away_score'])
            team2_scores.append(game['home_score'])
            team1_is_home = False
        
        quarters = _db_query("SELECT * FROM quarters WHERE game_id = ? ORDER BY quarter_num", (game['id'],))
        if quarters:
            for q in quarters[:4]:
                qnum = q['quarter_num']
                if team1_is_home:
                    team1_quarters[f'q{qnum}'].append(q['home_score'] or 0)
                    team2_quarters[f'q{qnum}'].append(q['away_score'] or 0)
                else:
                    team1_quarters[f'q{qnum}'].append(q['away_score'] or 0)
                    team2_quarters[f'q{qnum}'].append(q['home_score'] or 0)
    
    team1_quarters_avg = {k: round(sum(v)/len(v), 1) if v else 0 for k, v in team1_quarters.items()}
    team2_quarters_avg = {k: round(sum(v)/len(v), 1) if v else 0 for k, v in team2_quarters.items()}
    
    return jsonify({
        'games_count': len(games),
        'team1_avg': round(sum(team1_scores)/len(team1_scores), 1) if team1_scores else 0,
        'team2_avg': round(sum(team2_scores)/len(team2_scores), 1) if team2_scores else 0,
        'team1_quarters': team1_quarters_avg,
        'team2_quarters': team2_quarters_avg
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
