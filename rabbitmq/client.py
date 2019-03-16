#!/usr/bin/env python
import pika
import uuid
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

publicKeyFile = "./keys-client/publicKey.pem"
privateKeyFile = "./keys-client/privateKey.pem"

def signMessage(key, message):
    digest = SHA256.new()
    digest.update(message)
    signer = PKCS1_v1_5.new(key)
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

    '''
    #Save keys
    with open (privateKeyFile, "w") as prv_file:
        print("{}".format(privateKey.exportKey().decode('utf-8')), file=prv_file)

    with open (publicKeyFile, "w") as prv_file:
        print("{}".format(publicKey.decode('utf-8')), file=prv_file)
    '''
    return publicKey, privateKey


def getKey(keyFile):

    #Read key    
    if os.path.isfile(keyFile):
        with open (keyFile, "r") as myfile:
            key = RSA.importKey(myfile.read())
    #Generate private and public keys
    else:
        generateKey()
        getKey(keyFile)
    
    return key

class RpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n, topic):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key=topic,
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=n)
        while self.response is None:
            self.connection.process_data_events()
        return self.response

rpc = RpcClient()

####################################################################################
#####                             Send information                             #####
####################################################################################


##########################################
##       Get server's public key        ##
##########################################
body = ""
topic = "getPublicKey"

response = rpc.call(body, topic)
print(response)
keyPublicServer = RSA.importKey(response.decode("ascii"))

##########################################
## Send server registration information ##
##########################################

token = "aedfa6c3a114ccf9e72f056e1d7e5313"
email = "a@mail.com"
password = "mypassword"
publicKeyClient = getKey(publicKeyFile)
privateKeyClient = getKey(privateKeyFile)

#print(publicKeyClient.exportKey().decode("ascii"))
plainMessage = "{\"token\":\"%s\", \"email\":\"%s\", \"password\":\"%s\"}%s" % (token, email, password, publicKeyClient.exportKey().decode("ascii"))
cipher = encryptMessage(keyPublicServer, plainMessage.encode("utf-8"))

#plainMessage = "{\"email\":\"%s\", %s}"  % (email,data)
sensor = "HR" 
value = "37"
timestamp = "1537716885"
email = "a@mail.com"


plainMessage = []
plainMessage.append("{\"email\":\"%s\"}"  % (email))
plainMessage.append("{\"sensor\":\"%s\",\"value\":\"%s\",\"timestamp\":\"%s\"}"  % (sensor,value,timestamp))

p1 = plainMessage[0]
p2 = plainMessage[1]
cipher1 = encryptMessage(publicKeyClient, p2.encode("utf-8"))
in2 = p1.encode("utf-8") + cipher1
cipher2 = encryptMessage(publicKeyClient, in2)
dec1 = decryptMessage(privateKeyClient, cipher2)
print(dec1)

'''
plainMessage = []
plainMessage.append("{\"email\":\"%s\""  % (email))
plainMessage.append(",\"data\":[{\"sensor\":\"%s\",\"value\":\"%s\",\"timestamp\":\"%s\"}]}"  % (sensor,value,timestamp))

signed = encryptMessage(privateKeyClient, plainMessage[1].encode("utf-8"))
encrypt = encryptMessage(privateKeyClient, plainMessage[0].encode("utf-8") + signed)
'''

#print(encrypt)
#print(decryptMessage(publicKeyClient, encrypt))

topic = "register"
#response = rpc.call(cipher, topic)
#print(response)

##########################################
##           Send measurement           ##
##########################################
'''
publicKeyClient = getKey(publicKeyFile)
sensor = "HR" 
value = "37"
timestamp = "1537716885"
email = "a@mail.com"

plainMessage = "{\"sensor\":\"%s\",\"value\":\"%s\",\"timestamp\":\"%s\",\"email\":\"%s\"}%s" % (sensor,value,timestamp,email, publicKeyClient.exportKey().decode("ascii"))
cipher = encryptMessage(keyPublicServer, plainMessage.encode("utf-8"))
topic = "measurement"
response = rpc.call(cipher, topic)
print(response)
'''
# Send measurement
'''
sensor = "HR"
value = "37"
timestamp = "1537716885"
mail = "assddo@gmail.com"
message = "{\"sensor\":\"%s\",\"value\":\"%s\",\"timestamp\":\"%s\",\"mail\":\"%s\"}" % (sensor,value,timestamp,mail)
response = rpc.call(message, "routing_key")
print(" [.] Got %r" % response)
'''
