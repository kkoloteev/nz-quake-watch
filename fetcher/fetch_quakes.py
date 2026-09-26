import os
import time
import logging
import psycopg2
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('fetcher')

GEONET_URL = 'https://api.geonet.org.nz/quake?MMI=-1'
HEADERS = {'Accept': 'application/vnd.geo+json;version=2'}
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL_SECONDS', 300))

UPSERT_SQL = '''
    INSERT INTO quakes (public_id, time, latitude, longitude, depth, magnitude, mmi, locality, quality)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (public_id) DO UPDATE SET
        time = EXCLUDED.time,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        depth = EXCLUDED.depth,
        magnitude = EXCLUDED.magnitude,
        mmi = EXCLUDED.mmi,
        locality = EXCLUDED.locality,
        quality = EXCLUDED.quality,
        fetched_at = now()
'''

def fetch_quakes():
    resp = requests.get(GEONET_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()['features']

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def sync_once():
    features = fetch_quakes()
    conn = get_db_connection()
    cur = conn.cursor()
    for f in features:
        p = f['properties']
        lon, lat, *_ = f['geometry']['coordinates']
        cur.execute(UPSERT_SQL, (
            p['publicID'], p['time'], lat, lon,
            p['depth'], p['magnitude'], p['mmi'],
            p['locality'], p['quality'],
        ))
    conn.commit()
    cur.close()
    conn.close()
    log.info('Synced %d quakes', len(features))

if __name__ == '__main__':
    while True:
        try:
            sync_once()
        except Exception:
            log.exception('Fetch cycle failed')
        time.sleep(POLL_INTERVAL)