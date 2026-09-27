import os
import time
import json
import logging
import psycopg2
import requests
import pika

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('fetcher')

GEONET_URL = 'https://api.geonet.org.nz/quake?MMI=-1'
HEADERS = {'Accept': 'application/vnd.geo+json;version=2'}
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL_SECONDS', 300))
RABBITMQ_URL = os.environ['RABBITMQ_URL']

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
    RETURNING (xmax = 0) AS inserted
'''


def fetch_quakes():
    resp = requests.get(GEONET_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()['features']


def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def get_rabbitmq_channel():
    for attempt in range(10):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(exchange='quakes', exchange_type='topic', durable=True)
            return connection, channel
        except pika.exceptions.AMQPConnectionError:
            log.warning('RabbitMQ not ready yet, retrying (%d/10)', attempt + 1)
            time.sleep(5)
    raise RuntimeError('Could not connect to RabbitMQ after 10 attempts')


def publish_new_quake(channel, feature, public_id):
    p = feature['properties']
    lon, lat, *_ = feature['geometry']['coordinates']
    message = {
        'public_id': public_id,
        'time': p['time'],
        'latitude': lat,
        'longitude': lon,
        'depth': p['depth'],
        'magnitude': p['magnitude'],
        'mmi': p['mmi'],
        'locality': p['locality'],
        'quality': p['quality'],
    }
    channel.basic_publish(
        exchange='quakes',
        routing_key='quake.new',
        body=json.dumps(message),
        properties=pika.BasicProperties(content_type='application/json', delivery_mode=2),
    )
    log.info('Published new quake %s (%s, mag %.1f)', public_id, p['locality'], p['magnitude'])


def sync_once(channel):
    features = fetch_quakes()
    conn = get_db_connection()
    cur = conn.cursor()

    new_count = 0
    for f in features:
        p = f['properties']
        lon, lat, *_ = f['geometry']['coordinates']
        cur.execute(UPSERT_SQL, (
            p['publicID'], p['time'], lat, lon,
            p['depth'], p['magnitude'], p['mmi'],
            p['locality'], p['quality'],
        ))
        (inserted,) = cur.fetchone()
        if inserted:
            new_count += 1
            publish_new_quake(channel, f, p['publicID'])

    conn.commit()
    cur.close()
    conn.close()
    log.info('Synced %d quakes (%d new)', len(features), new_count)


if __name__ == '__main__':
    rmq_connection, rmq_channel = get_rabbitmq_channel()
    try:
        while True:
            try:
                sync_once(rmq_channel)
            except Exception:
                log.exception('Fetch cycle failed')
            time.sleep(POLL_INTERVAL)
    finally:
        rmq_connection.close()
