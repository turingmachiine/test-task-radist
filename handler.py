import asyncio
import json
from gino import Gino
from aio_pika import connect, IncomingMessage, ExchangeType

loop = asyncio.get_event_loop()
db = Gino()


class MessageDb(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer(), primary_key=True)
    receiver = db.Column(db.Unicode())
    msg_type = db.Column(db.Unicode())
    body = db.Column(db.Unicode())
    status = db.Column(db.Unicode())


async def on_message(message: IncomingMessage):
    with message.process():
        temp_str = message.body.decode().replace("\'", "\"")
        json_message = json.loads(temp_str)
        # Creating database connection
        await db.set_bind('postgresql://postgres/radist_db')
        # Create tables
        await db.gino.create_all()

        status, result = await MessageDb.update.values(
        status='Обработано').where(
            MessageDb.id == json_message['id']).gino.status()
        print("     Received message %r" % message.body.decode())


async def main(binding_key):
    # Perform connection
    connection = await connect(
        "amqp://guest:guest@localhost/", loop=loop
    )

    # Creating a channel
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    messages_exchange = await channel.declare_exchange('messages', ExchangeType.DIRECT)
    # Declaring queue
    queue = await channel.declare_queue(
        '{}_queue'.format(binding_key), durable=True
    )

    await queue.bind(messages_exchange, routing_key=binding_key)

    # Start listening the queue with name 'task_queue'
    await queue.consume(on_message)

if __name__ == "__main__":
    key = input()
    loop = asyncio.get_event_loop()
    loop.create_task(main(key))

    # we enter a never-ending loop that waits for data and runs
    # callbacks whenever necessary.
    print("Waiting for messages.")
    loop.run_forever()
