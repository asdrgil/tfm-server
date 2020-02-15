from pymongo import MongoClient

mongoClient = MongoClient('localhost:27017').tfm
rowsPerPage = 15
counterSleepTmp = 1*15*1000
tokenLength = 6