#!/usr/bin/env python
import pika
from pymongo import MongoClient, errors
import json
import re
import bcrypt

#Global variables
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
topics = ["token", "register", "measurement"]
token = ""
mongoClient = MongoClient('localhost:27017').tfm

#Output queues
for i in topics:
    channel.queue_declare(queue=i)

def findToken(token):
    tokenQuery = mongoClient.token.find_one({'token' : token})

    if tokenQuery == None:
        return 0
    elif tokenQuery["used"] == 1:
        return 1
    return 200

def register(data):
    try:
    
        #Check if mail field has a valid email format
        if re.match(r"[^@]+@[^@]+\.[^@]+", data["mail"]) == None: 
            return 2
            
        #Minimum password length is 5 characters
        if len(data["passwd"]) < 5:
            return 3
        
        #TODO: encrypt password before storing it in the database
        #data["passwd"] = bcrypt.hashpw(password, bcrypt.gensalt())
        
        #Check if the email is already registered
        if mongoClient.user.find_one({'mail' : data["mail"]}):
            return 4
        
        mongoClient.user.insert_one(data)
        mongoClient.token.replace_one({'token': token}, {'token': token, 'used': 1})
    
    except ValueError: #Body is not in json format
        return 0
    except KeyError: #Missing key mail or passwd
        return 1

    return 200

def measurement(data):
    try:
        #TODO: Add some authentification before allowing to send sensorized data
        
        if mongoClient.measurement.find_one({'sensor' : data["sensor"], 'timestamp' : data["timestamp"], 'mail' : data["mail"]}):
            return 3
        
        mongoClient.measurement.insert_one(data)
    
    except ValueError: #Body is not in json format
        return 0
    except KeyError: #Missing key mail or passwd
        return 1

    return 200
    

def on_request(ch, method, props, body):
    response = -1
    global token

    print("Routing key: %s" % method.routing_key)
    
    if method.routing_key == "token":
        token = body.decode("ascii")
        response = findToken(token)
    elif method.routing_key == "register":
        try:
            response = register(json.loads(body.decode("ascii")))
        except ValueError as e:
            response = 5
    elif method.routing_key == "measurement":
        response = measurement(json.loads(body.decode("ascii")))
    
    #response = fib(n)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag = method.delivery_tag)


if __name__ == "__main__":
    channel.basic_qos(prefetch_count=1)

    #Input topics
    for i in topics:
        channel.basic_consume(on_request, queue=i)

    print(" [x] Awaiting RPC requests")
    channel.start_consuming()
