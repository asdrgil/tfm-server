from pymongo import MongoClient

mongoClient = MongoClient('localhost:27017').tfm
rowsPerPage = 10
registerTokenLength = 6
communicationTokenLength = 10
maxSelectlength = 24

urlPrefix = "/termoira"
host="0.0.0.0"
port=80

reasonAnger = ["", "Rechazo, exclusión, ser ignorado", "Sentirse incomprendido", "Inseguridad", "Engaño", "Vejaciones verbales", "Sentirse avergonzado", "Frustración o impotencia", "Decepción", "Tristeza", "Miedo a perder algo", "Impaciencia", "Ataque físico"]
