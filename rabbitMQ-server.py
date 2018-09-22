import pika
from pymongo import MongoClient, errors

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='tokens')

def findToken(token):
    mongoToken = MongoClient('localhost:27017').tfm.token
    token = token.decode('ascii')
    tokenQuery = mongoToken.find_one({'token' : token})

    if tokenQuery == None:
        return 0
    elif tokenQuery["used"] == 1:
        return 1
    return 2    

def on_request(ch, method, props, body):
    token = body
    response = findToken(token)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag = method.delivery_tag)



if __name__ == "__main__":
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='tokens')

    print(" [x] Awaiting RPC requests")
    channel.start_consuming()
