import os
import time
import json
import logging
import pika

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('notifier')

RABBITMQ_URL = os.environ['RABBITMQ_URL']


def on_message(channel, method, properties, body):
    quake = json.loads(body)
    # TODO: заменить на реальную отправку в Telegram
    log.info(
        'NEW QUAKE: %s | mag %.1f | MMI %d | depth %.1f km | %s',
        quake['public_id'], quake['magnitude'], quake['mmi'],
        quake['depth'], quake['locality'],
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection = None
    for attempt in range(10):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            break
        except pika.exceptions.AMQPConnectionError:
            log.warning('RabbitMQ not ready yet, retrying (%d/10)', attempt + 1)
            time.sleep(5)
    if connection is None:
        raise RuntimeError('Could not connect to RabbitMQ after 10 attempts')

    channel = connection.channel()
    channel.exchange_declare(exchange='quakes', exchange_type='topic', durable=True)

    channel.queue_declare(queue='quake_notifications', durable=True)
    channel.queue_bind(exchange='quakes', queue='quake_notifications', routing_key='quake.new')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='quake_notifications', on_message_callback=on_message)

    log.info('Waiting for messages on quake_notifications...')
    channel.start_consuming()


if __name__ == '__main__':
    main()
