import os
import binascii
from pymongo import MongoClient, errors
import json

mongoToken = MongoClient('localhost:27017').tfm.token

def generateToken(numberTokens):
    
    token = binascii.hexlify(os.urandom(16)).decode("utf-8")

    for i in range(numberTokens):
          #Tokens must be unique
          while(mongoToken.find_one({'token' : token})):
              token = binascii.hexlify(os.urandom(16)).decode("utf-8")

          tokenString = "{ \"token\" : \"" + token + "\", \"used\" : 0 }"
          print("[DEBUG] Inserting token " + token)
          mongoToken.insert_one(json.loads(tokenString))

if __name__ == "__main__":
    generateToken(3)

