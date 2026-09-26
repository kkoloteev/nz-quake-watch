import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, jsonify

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/quakes')
def api_quakes():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT public_id, time, latitude, longitude, depth, magnitude, mmi, locality, quality
        FROM quakes
        WHERE quality != 'deleted'
        AND time > now() - interval '48 hours'
        ORDER BY time DESC
        LIMIT 500
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    features = [{
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [row['longitude'], row['latitude']]
        },
        'properties': {
            'public_id': row['public_id'],
            'time': row['time'].isoformat(),
            'depth': row['depth'],
            'magnitude': row['magnitude'],
            'mmi': row['mmi'],
            'locality': row['locality'],
            'quality': row['quality'],
        }
    } for row in rows]

    return jsonify({'type': 'FeatureCollection', 'features': features})
