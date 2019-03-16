
import pika
from pymongo import MongoClient, errors
import json
import re
import bcrypt
import datetime
import sys
import os
import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
import ast
import math

#Global variables
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
topics = ["getPublicKey", "register", "measurement"]
token = ""
mongoClient = MongoClient('localhost:27017').tfm
publicKeyFile = "./keys/publicKey.pem"
privateKeyFile = "./keys/privateKey.pem"

neccesaryKeys = {"register" : ['email', 'password', 'token']}

#Output queues
for i in topics:
    channel.queue_declare(queue=i)

def mongoController(method, collection, inputData):
    #try:
    if method == "find_one":
        return mongoClient[collection].find_one(inputData)
    elif method == "insert_one":
        return mongoClient[collection].insert_one(inputData)
    elif method == "replace_one":
        return mongoClient[collection].replace_one(inputData)
    #except pymongo.errors.ConnectionFailure:
    #    sys.exit("[ERROR] Could not connect to Mongo server")

def signMessage(key, message):
    digest = SHA256.new()
    digest.update(message)
    signer = PKCS1_v1_5.new(keyPrivate)
    return digest, signer.sign(digest)

def verifySignMessage(digest, sig, keyPublic):
    verifier = PKCS1_v1_5.new(keyPublic)
    return verifier.verify(digest, sig)
    
def encryptMessage(key, message):
    batchSize = 128
    batches = math.ceil(len(message)/batchSize)
    result = b""
    i = 0
    
    while i < batches:
        #print(message[i*batchSize:(i+1)*batchSize])
        result += key.encrypt(message[i*batchSize:(i+1)*batchSize], 0)[0]
        #print(result)
        i += 1
    #print(result)
    return result

def decryptMessage(key, message):
    batchSize = 128
    batches = math.ceil(len(message)/batchSize)
    print("batches : %d" % (batches))
    result = b""
    i = 0
    
    while i < batches:
        result += key.decrypt((message[i*batchSize:(i+1)*batchSize],))
        #print((message[i*batchSize:(i+1)*batchSize],))
        i += 1
    return result

def generateKey():
    random = Random.new().read
    privateKey = RSA.generate(1024, random)
    publicKey = privateKey.publickey()

    #Save keys
    with open (privateKeyFile, "w") as prv_file:
        print("{}".format(privateKey.exportKey().decode('utf-8')), file=prv_file)

    with open (publicKeyFile, "w") as prv_file:
        print("{}".format(publicKey.decode('utf-8')), file=prv_file)


def getKey(keyFile):

    publicKey = None

    #Read public key    
    if os.path.isfile(keyFile):
        with open (keyFile, "r") as myfile:
            key = RSA.importKey(myfile.read())
    #Generate private and public keys
    else:
        generateKey()
        getKey(keyFile)

    return key

def storeTemporalPublicKey(clientKey):
    if not mongoController("find_one", "temporalPublicKeys", clientKey):
        mongoController("insert_one", "temporalPublicKeys", clientKey)
        return 1
    return 0


def findToken(token):
    tokenQuery = mongoController("find_one", "token", token)
    if tokenQuery == None:
        return 0
    elif tokenQuery["used"] == 1:
        return 1
    return 200

def register(data, publicKeyClient):

    #Check if there are any missing parameters
    if len(set(neccesaryKeys["register"]) & set(data)) != 3:
        response = 404

    #Check email is correctly formatted
    if re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]) is None:
        response = 404

    #Password must have at least 5 characters
    if len(data["password"]) < 5:
        response = 404

    #View if the current token is in Mongo's database
    mongoToken = mongoController("find_one", "token", {"token" : data["token"]})

    #Token not inserted in the database
    if mongoToken is None:
        response = 404
        
    #Registered token but already in use
    elif "email" in mongoToken is None:
        response = 404

    #Token inserted in the database and not used
    else:
        #Find if the current email is already used
        mongoEmail = mongoController("find_one", "token", {"email" : data["email"]})
        
        #Email already used (it should be unique for each user)
        if mongoEmail is not None:
            response = 404
        
        #Email is not used
        #Insert register in the database
        else:
            #Store the password's hash
            salt = bcrypt.gensalt()
            hashPassword = bcrypt.hashpw(data["password"].encode("utf-8"), salt)
            
            mongoClient["token"].update_one({'token': data["token"]}, {"$set": {"email" : data["email"], "password" : hashPassword}})
            
            
            #Save output to file
            with open(data["email"] + "-public.pem", "w") as text_file:
                text_file.write(publicKeyClient)
            
            response = 200
        
        '''
        #Check if mail field has a valid email format
        if re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]) not None: 
            mail = True
            
        #Minimum password length is 5 characters
        if len(data["password"]) < 5:
            return 3
        
        #TODO: encrypt password before storing it in the database
        #data["passwd"] = bcrypt.hashpw(password, bcrypt.gensalt())
        
        #Check if the email is already registered
        if mongoController("find_one", "user", {'email' : data["email"]}):
            return 4
        
        mongoController("insert_one", "user", data)
        mongoController("replace_one", "token", {'token': token, 'used': 1})
        '''

    return 200

def measurement(data):
    print("IN")
    '''
    try:
        if mongoController("find_one", "measurement", {'sensor' : data["sensor"], 'timestamp' : data["timestamp"], 'email' : data["email"]}):
            return 3
        
        mongoController("insert_one", "measurement", data)
    
    except ValueError: #Body is not in json format
        return 0
    except KeyError: #Missing key mail or passwd
        return 1
    '''
    return 200
    

def on_request(ch, method, props, body):

    response = "No"
    global token

    print("Routing key: %s" % method.routing_key)

    #data = json.loads(body.decode("ascii"))

    if method.routing_key == "getPublicKey":
        response = getKey(publicKeyFile).exportKey().decode("ascii")
    elif method.routing_key == "register":
        plainData = decryptMessage(getKey(privateKeyFile), body).decode("utf-8")
        registerData = json.loads(plainData[:plainData.find("}") + 1])
        publicKeyClient = plainData[plainData.find("}") + 1:]
        
        register(registerData, publicKeyClient)
        
    elif method.routing_key == "measurement":
        plainData = decryptMessage(getKey(privateKeyFile), body).decode("utf-8")
        data = json.loads(plainData[:plainData.find("}") + 1])
        publicKeyClient = plainData[plainData.find("}") + 1:]
        #response = measurement(data)

    #response = fib(n)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag = method.delivery_tag)


if __name__ == "__main__":
    try:
        '''
        keyPublic = getKey(publicKeyFile)
        keyPrivate = getKey(privateKeyFile)
        message = "abcdefghijklmnopqrstuvwxyz".encode("utf-8")
        
        digest, sig = signMessage(keyPrivate, message)

        print(verifySignMessage(digest, sig, keyPublic))
        
        cipher = encryptMessage(keyPublic, message)
        print(decryptMessage(keyPrivate, cipher))
        '''


        channel.basic_qos(prefetch_count=1)

        #Input topics
        for i in topics:
            channel.basic_consume(on_request, queue=i)

        print(" [x] Awaiting RPC requests")
        channel.start_consuming()

    except KeyboardInterrupt:
        print("\nExiting program...")
        
