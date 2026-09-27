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


def connect():
    for attempt in range(10):
        try:
            return pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except pika.exceptions.AMQPConnectionError:
            log.warning('RabbitMQ not ready yet, retrying (%d/10)', attempt + 1)
            time.sleep(5)
    raise RuntimeError('Could not connect to RabbitMQ after 10 attempts')


def consume_once():
    connection = connect()
    channel = connection.channel()
    channel.exchange_declare(exchange='quakes', exchange_type='topic', durable=True)

    # durable=True — очередь переживает перезапуск RabbitMQ (важно вместе с delivery_mode=2 у fetcher)
    channel.queue_declare(queue='quake_notifications', durable=True)
    channel.queue_bind(exchange='quakes', queue='quake_notifications', routing_key='quake.new')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='quake_notifications', on_message_callback=on_message)

    log.info('Waiting for messages on quake_notifications...')
    try:
        channel.start_consuming()  # блокирует до обрыва соединения или явной остановки
    finally:
        try:
            connection.close()
        except Exception:
            pass


def main():
    # start_consuming() блокирует, пока соединение живо; если RabbitMQ
    # перезапустится или сеть оборвётся — он выбросит исключение и выйдет
    # отсюда. Внешний while True гарантирует, что мы не просто упадём
    # и останемся мёртвыми, а переподключимся и продолжим слушать очередь.
    while True:
        try:
            consume_once()
        except (pika.exceptions.AMQPError, pika.exceptions.StreamLostError):
            log.exception('RabbitMQ connection lost, reconnecting')
            time.sleep(5)


if __name__ == '__main__':
    main()