from flask_login import current_user
from pymongo import MongoClient, errors
from flask_login import current_user
import random
import string
from datetime import datetime
import re

#Constants
mongoClient = MongoClient('localhost:27017').tfm

def getCurentUser():
    current_user.get_id()
    
def searchPatterns(form):

    result = []
    query = {"therapist":current_user.get_id()}

    #NAME
    if len(form.name.data.strip()) > 0:
        query.update({"name": re.compile('.*' + form.name.data.strip() + '.*', re.IGNORECASE)})

    #DESCRIPTION
    if len(form.description.data.strip()) > 0:
        query.update({"description": re.compile('.*' + form.description.data.strip() + '.*', re.IGNORECASE)})


    #IDs of the patterns to be retrieved (auxiliary variable)
    patternIds = set([])

    #PATIENTS
    #Make an OR query of the selected patients
    if len(form.patients.data) > 0:

        #Obtains the ids for the selected patients but not in Mongo format
        queryPatients1 = []

        #Obtains the ids for the selected patient in Mongo format
        queryPatients2 = []

        for elem in form.patients.data:
            queryPatients1.append({'id': int(elem)})

        cursor = mongoClient["patients"].find({"$or": queryPatients1})

        for cur in cursor:
            if "patterns" in cur:
                for patt in cur["patterns"]:
                    if patt not in patternIds:
                        queryPatients2.append({'id': int(patt)})
                        patternIds.add(int(patt))

        query.update({"$or": queryPatients2})


    #GROUPS
    #Make an OR query of the selected groups
    if len(form.groups.data) > 0:
        queryGroups = []

        cursor = mongoClient["groups"].find({"id" : { "$in": list(map(int, form.groups.data))}})

        #Add the id of the associated patterns
        for cur in cursor:
            if "patterns" in cur:
                for patt in cur["patterns"]:
                    if patt not in patternIds:
                        queryGroups.append({'id': int(patt)})
                        patternIds.add(int(patt))

        query.update({"$or": queryGroups})

    #INTENSITIES
    if len(form.intensities.data) > 0:
        query.update({"intensities": { "$in": list(map(int, form.intensities.data))}})

    cursorPatterns = mongoClient["patterns"].find(query)

    for cur in cursorPatterns:
        description = "" if "description" not in cur else cur["description"]

        intensity1 = "No" #Yellow
        intensity2 = "No" #Orange
        intensity3 = "No" #Red

        intensities = []

        if "intensities" in cur:
            intensities = cur["intensities"]

            if 1 in cur["intensities"]:
                intensity1 = "Sí"
            if 2 in cur["intensities"]:
                intensity2 = "Sí"
            if 3 in cur["intensities"]:
                intensity3 = "Sí"

        result.append({"id": cur["id"], "name": cur["name"], "description": description, \
            "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3})

    return result

def searchPatients(form):

    result = []
    query = {"therapist":current_user.get_id()}

    #NAME
    if len(form.name.data.strip()) > 0:
        query.update({"name": re.compile('.*' + form.name.data.strip() + '.*', re.IGNORECASE)})

    #SURNAME1
    if len(form.surname1.data.strip()) > 0:
        query.update({"surname1": re.compile('.*' + form.surname1.data.strip() + '.*', re.IGNORECASE)})

    #SURNAME2
    if len(form.surname2.data.strip()) > 0:
        query.update({"surname2": re.compile('.*' + form.surname2.data.strip() + '.*', re.IGNORECASE)})


    #AGE
    if len(form.age.data.strip()) > 0:
        query.update({"age": int(form.age.data)})

    #PATTERNS
    if len(form.patterns.data) > 0:
        query.update({"patterns": { "$in": list(map(int, form.patterns.data))}})


    #GROUPS
    #Make an OR query of the selected groups
    if len(form.groups.data) > 0:
        patientIds = set([])
        queryGroups = []

        cursor = mongoClient["groups"].find({"id" : { "$in": list(map(int, form.groups.data))}})

        #Add the id of the associated patterns
        for cur in cursor:
            if "patients" in cur:
                for pati in cur["patients"]:
                    if pati not in patientIds:
                        queryGroups.append({'id': int(pati)})
                        patientIds.add(int(pati))

        query.update({"$or": queryGroups})

    
    ###################

    cursor = mongoClient["patients"].find(query)

    for cur in cursor:
        result.append({"id": cur["id"], "name": cur["name"] , "surname1": cur["surname1"], \
            "surname2": cur["surname2"], "age": cur["age"]})

    return result


def searchGroups(form):

    result = []
    query = {"therapist":current_user.get_id()}

    #NAME
    if len(form.name.data.strip()) > 0:
        query.update({"name": re.compile('.*' + form.name.data.strip() + '.*', re.IGNORECASE)})

    #DESCRIPTION
    if len(form.description.data.strip()) > 0:
        query.update({"description": re.compile('.*' + form.description.data.strip() + '.*', re.IGNORECASE)})

    #PATIENTS
    if len(form.patients.data) > 0:
        query.update({"patients": { "$in": list(map(int, form.patients.data))}})

    #PATTERNS
    if len(form.patterns.data) > 0:
        query.update({"patterns": { "$in": list(map(int, form.patterns.data))}})

    
    ###################

    cursor = mongoClient["groups"].find(query)

    for cur in cursor:
        description = ""
        if "description" in cur:
            description = cur["description"]
        result.append({"id": cur["id"], "name": cur["name"] , "description": description})

    return result

def deletePattern(patternId):
    mongoClient["patterns"].delete_one(int(patternId))
    #TODO: más adelante, se podrán añadir eliminaciones más complejas, como quitar su ID de los grupos, de las mediciones etc

def insertPatternTmp(msg):
    therapist = current_user.get_id()
    error = ""
    msg = msg.split(",")
    windowId = msg[0]
    patternName = msg[1]
    patternDescription = msg[2]

    intensities = []

    if str(msg[3]) == "1":
        intensities.append(1)

    if str(msg[4]) == "1":
        intensities.append(2)

    if str(msg[5]) == "1":
        intensities.append(3)


    #If there is not already a pattern with the given name for the given therapist: raise error
    if mongoClient["patterns"].count_documents({"name": patternName, "therapist": therapist, \
        "windowId": {"$exists":False}}) == 0 and mongoClient["tmpPatterns"]\
        .count_documents({"windowId":windowId, "name":patternName}) == 0:

        idPattern = 1

        if mongoClient["patterns"].count_documents({}) > 0:
            cursor = mongoClient["patterns"].find({}).sort("id",-1).limit(1)
            
            for cur in cursor:
                idPattern = cur["id"] + 1

        mongoClient["patterns"].insert_one({"id":idPattern, 'name': patternName, 'description': patternDescription, \
            'intensities': intensities, "windowId":windowId, "therapist":therapist})
        mongoClient["tmpPatterns"].insert_one(\
            {"id": idPattern, "pattType": "insertPattern", "windowId": windowId, "name":patternName})
    else:
        error = "Ya existe una pauta con este nombre"

    body = getTmpPatterns(windowId)
    return body, error

def getTmpPatterns(windowId, outputFormat="str"):
    if outputFormat == "str":
        result = ""
    else:
        result = []

    #Obtain all the patterns of the given windowId
    if mongoClient["tmpPatterns"].count_documents({"windowId": windowId}) > 0:
        queryPatterns = []

        cursor = mongoClient["tmpPatterns"].find({"windowId": windowId})

        #First, it queries the patterns just by id in order to later obtain it's content
        for cur in cursor:
            queryPatterns.append({'id': int(cur["id"])})

        if mongoClient["patterns"].count_documents({"$or": queryPatterns}) > 0:
            cursor2 = mongoClient["patterns"].find({"$or": queryPatterns}).sort("name", 1).sort("description", 1)

            #Iterate through all the patterns
            for cur2 in cursor2:

                intensity1 = "No"
                intensity2 = "No"
                intensity3 = "No"

                if "intensities" in cur2:
                    if 1 in cur2["intensities"] or "1" in cur2["intensities"]:
                        intensity1 = "Sí"

                    if 2 in cur2["intensities"] or "2" in cur2["intensities"]:
                        intensity2 = "Sí"

                    if 3 in cur2["intensities"] or "3" in cur2["intensities"]:
                        intensity3 = "Sí"

                if outputFormat == "str":
                    cursorTmpPatt = mongoClient["tmpPatterns"].find_one({"name":cur2["name"]})
                    pattType = "selectPatt"
                    if "pattType" in cursorTmpPatt:
                        pattType = cursorTmpPatt["pattType"]
                    result += str(cur2["id"]) + "," + cur2["name"]+ "," + cur2["description"] + "," + \
                    intensity1 + "," + intensity2 + "," + intensity3 + "," + pattType + ";"
                else:
                    result.append({"name": cur["name"], "description": cur["description"], "id": str(cur["id"])})

    if outputFormat == "str" and len(result) > 0 and result[-1] == ";":
        result = result[:-1]

    return result

def getPatternsSelectPattern(msg):
    therapist = current_user.get_id()
    msg = msg.split(",")
    windowId = msg[0]
    pattIds = msg[1:]

    print(windowId)

    mongoClient["tmpPatterns"].delete_many({"windowId": windowId, "pattType": "selectPatt"})

    result = ""

    if len(pattIds[0]) > 0:
        
        #Insert on tmp all patterns checked on the select making sure that there are no duplicates
        for patt in pattIds:
            if mongoClient["tmpPatterns"].count_documents({"id": patt, "windowId": windowId}) == 0:
                mongoClient["tmpPatterns"].insert_one({"id": patt, "pattType": "selectPatt", "windowId": windowId})    

    return getTmpPatterns(windowId)

def getPatternsSelectGroup(msg):
    therapist = current_user.get_id()
    msg = msg.split(",")
    windowId = msg[0]
    patientId = msg[1]
    groupIds = msg[2:]

    mongoClient["tmpPatterns"].delete_many({"windowId": windowId, "pattType": "selectGroup"})

    result = ""

    if len(groupIds[0]) > 0:

        queryGroups = []

        for elem in groupIds:
            queryGroups.append({'id': int(elem)})

        if mongoClient["groups"].count_documents({"$or": queryGroups}) > 0:

            #Obtener las pautas para las que se han incluido en el select
            cursor = mongoClient["groups"].find({"$or": queryGroups}).sort("name", 1)
            patterns = []

            #Incluir el id de todas las pautas en el registro temporal de grupo
            for cur in cursor:
                if "patterns" in cur:
                    for patt in cur["patterns"]:
                        #Se hace la comprobación para no meter duplicados de pautas que puedan pertenecer a varios grupos
                        if patt not in patterns:
                            patterns.extend(str(patt))
                            mongoClient["tmpPatterns"].insert_one({"id": patt, "pattType": "selectGroup", \
                                "windowId": windowId})

    return getTmpPatterns(windowId)

#TODO: check usages (added gender)
def insertPatient(windowId, name, surname1, surname2, age, gender, groups, synced):

    cursor = mongoClient["patients"].find({}).sort("id",-1).limit(1)
    idPatient = 1
    for cur in cursor:
        idPatient = cur["id"] + 1

    patternsAll = getTmpPatterns(windowId)

    mongoClient["patients"].insert_one({"name":name, "surname1":surname1, "surname2":surname2, "age":age, \
        "gender":gender, "wristbandCallibated": False, "synced":synced, "id":idPatient, "patterns": patternsAll, \
        "therapist":current_user.get_id()})

    #Update all selected groups to include the given patient
    for group in groups:
        mongoClient["groups"].update({"id": int(group)}, {"$push": {"patients":idPatient}})

def getUnlinkPattern(msg):
    therapist = current_user.get_id()
    msg = msg.split(",")
    windowId = msg[0]
    pattId = int(msg[1])
    patientId = "" if len(msg) < 3 else msg[2]

    mongoClient["tmpPatterns"].delete_one({"windowId": windowId, "id": pattId})

    #If the pattern is not new, just unlink it from the patient. Otherwise, delete it permanently
    if mongoClient["patterns"].count_documents({"therapist":therapist, "id":pattId, "windowId": {"$exists":False}}) > 0:
        mongoClient["patients"].update_one({"id":patientId}, {"$pull": {"patterns":pattId}})
    else:
        mongoClient["patterns"].delete_one({"therapist":therapist, "id":pattId})

    tmpPatterns = getTmpPatterns(windowId)

    return tmpPatterns

def getEpisodesCursor(timestampFrom, timestampTo, idPatient):
    #Query based on an answer in StackOverflow by @Valijon
    cursor = mongoClient["measurements"].aggregate([
        {
        "$facet": {
          "alerts": [
            {
              "$match": {
                "value": 0,
                "patient":idPatient,
                "tmstamp": {"$gte": timestampFrom, "$lte": timestampTo}
              }
            },
            {
              "$group": {
                "_id": "",
                "ids": {
                  "$push": "$_id"
                }
              }
            }
          ],
          "episodes": [
            {
              "$match": {
                "value": {
                  "$gt": 0
                }
              }
            }
          ]
        }
      },
      {
        "$unwind": "$alerts"
      },
      {
        "$addFields": {
          "alert_idx": "$alerts.ids"
        }
      },
      {
        "$unwind": "$alerts.ids"
      },
      {
        "$project": {
          "v": {
            "$filter": {
              "input": "$episodes",
              "cond": {
                "$and": [
                  {
                    "$gt": [
                      "$$this._id",
                      "$alerts.ids"
                    ]
                  },
                  {
                    "$lt": [
                      "$$this._id",
                      {
                        "$arrayElemAt": [
                          "$alert_idx",
                          {
                            "$sum": [
                              {
                                "$indexOfArray": [
                                  "$alert_idx",
                                  "$alerts.ids"
                                ]
                              },
                              1
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          }
        }
      },
      {
        "$match": {
          "v": {
            "$ne": []
          },
          
        }
      }
    ])

    return cursor

def getMultipleEpisodes(timestampFrom, timestampTo, idPatient):
    result = []
    cursor = getEpisodesCursor(timestampFrom, timestampTo, idPatient)

    totalAlerts = [0, 0, 0]

    for episode in cursor:
        firstDateTimestamp = 0
        lastDateTimestamp = 0
        firstAlert = True
        for alert in episode["v"]:

            if firstAlert:
                firstAlert = False
                firstDateTimestamp = int(alert["tmstamp"])

            lastDateTimestamp = int(alert["tmstamp"])

            totalAlerts[alert["value"] -1] += 1

        dateFirst = datetime.fromtimestamp(firstDateTimestamp)
        dateLast = datetime.fromtimestamp(lastDateTimestamp)

        result.append({"firstDate": dateFirst.strftime("%d/%m/%Y, %H:%M:%S"), \
            "lastDate":dateLast.strftime("%d/%m/%Y, %H:%M:%S"), "timestampFrom":timestampFrom, \
            "timestampTo":timestampTo, "alerts1": totalAlerts[0], "alerts2": totalAlerts[1], \
            "alerts3": totalAlerts[2]})

    return result

def getOneEpisode(timestampFrom, timestampTo, idPatient):
    #plotData = ""
    rows = []
    cursor = getEpisodesCursor(timestampFrom, timestampTo, idPatient)

    for episode in cursor:
        for alert in episode["v"]:
            currentDate = datetime.fromtimestamp(int(alert["tmstamp"]))
            rows.append({"date": currentDate.strftime("%d/%m/%Y, %H:%M:%S"), "alertLevel": alert["value"]})
            #[Date.UTC(2007, 0, 1, 0, 0, 0), 0.7537]
            #plotData += "Date.UTC(), {}"
    return rows

def generateUniqueRandom(collection, field):
    token = ''.join(random.choice('0123456789ABCDEF') for i in range(6))

    while mongoClient[collection].find({field:token}).count() > 0:
        generateUniqueRandom(token)

    return token