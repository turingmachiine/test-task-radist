import asyncio
import json
import os

import aio_pika
from aiohttp import web
from gino import Gino
from aio_pika import connect, Message, DeliveryMode, ExchangeType

db = Gino()
data_source = input()

class MessageDb(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer(), primary_key=True)
    receiver = db.Column(db.Unicode())
    msg_type = db.Column(db.Unicode())
    body = db.Column(db.Unicode())
    status = db.Column(db.Unicode())


async def hello(request):
    return web.Response(text="Hello, world")


app = web.Application()
app.add_routes([web.get('/', hello)])

routes = web.RouteTableDef()


async def main():
    await db.set_bind(data_source)
    # Create tables
    await db.gino.create_all()


asyncio.get_event_loop().run_until_complete(main())


@routes.get('/')
async def hello(request):
    return web.Response(text="Hello, world")


@routes.get('/messages/{id}')
async def get_message(request):
    message = await MessageDb.query.where(MessageDb.id == int(request.match_info['id'])).gino.first()
    print(message.status)

    return web.Response(body=json.dumps([message.id, message.status]))


async def send_to_consumer(message_text, routing_key):
    try:
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1/", loop=asyncio.get_event_loop()
        )

        channel = await connection.channel()  # type: aio_pika.Channel
        messages_exchange = await channel.declare_exchange('messages', ExchangeType.DIRECT)

        await messages_exchange.publish(
            aio_pika.Message(
                body='{}'.format(message_text).encode(),
                delivery_mode=DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )

        await connection.close()
    except RuntimeError:
        pass


@routes.post('/webhooks/{key}')
async def send_message(request):
    key = request.match_info['key']
    data = await request.json()
    temp_msg = await MessageDb.create(receiver=data['receiver'],
                                      msg_type=data['type'],
                                      body=data['body'],
                                      status='Получено')
    data['id'] = temp_msg.id
    await send_to_consumer(data, key)
    return web.Response(body=json.dumps(['Успешно', temp_msg.id]))


app = web.Application()
app.add_routes(routes)
web.run_app(app)
