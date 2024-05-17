import json
import os
import sys
from datetime import datetime

import openai
from flask import Flask
import pika
from openai import OpenAI

app = Flask(__name__)

# Set up RabbitMQ connection parameters
rabbitmq_host = 'localhost'
rabbitmq_exchange = 'amq.direct'
rabbitmq_queue = 'gpt-queue'
rabbitmq_response_queue = 'stt-response'

# Set up OpenAI API key
client = OpenAI(api_key='sk-proj-M9c5VBJJmoh6IwU9zVe7T3BlbkFJ2OBi2BcYA6SZh8yYYDMO')

def send(body):
    connection_response = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host))
    channel_response = connection_response.channel()

    channel_response.queue_declare(queue=rabbitmq_response_queue, durable=True)

    channel_response.basic_publish(exchange=rabbitmq_exchange, routing_key='stt-response', body=body)


def call_chatgpt_api(text, prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",

        messages=[
            {"role": "system", "content": text},
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content


def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()
    channel.exchange_declare(exchange=rabbitmq_exchange, durable=True)
    channel.queue_declare(queue=rabbitmq_queue, durable=True)

    def callback(ch, method, properties, body):
        message = json.loads(body)
        uid = message.get('uid', '')
        rid = message.get('rid', '')
        aid = message.get('aid', '')
        text = message.get('text', '')
        prompt = message.get('prompt', '')

        if text and prompt:
            print(f"Received message with text: {text} and prompt: {prompt}")
            response_text = call_chatgpt_api(text, prompt)
            print(f"Response from ChatGPT: {response_text}")

            response_message = {
                'uid': uid,
                'rid': rid,
                'aid': aid,
                'response': response_text
            }

            send(json.dumps(response_message))
        else:
            print("Message does not contain required fields 'text' and 'prompt'")

    channel.basic_consume(queue=rabbitmq_queue, on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
