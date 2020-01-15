from flask_login import current_user
from pymongo import MongoClient, errors
from flask_login import current_user
import random
import string
from datetime import datetime
import re
import math
from .constants import mongoClient, rowsPerPage

def getCurentUser():
    current_user.get_id()

def searchPatterns(form, pageNum=1):

    numberRows = 0
    numberPages = 0
    rows = []

    query = {"therapist":current_user.get_id(), "windowId": {"$exists":False}}

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

    numberTotalRows = mongoClient["patterns"].count_documents(query)
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    cursorPatterns = mongoClient["patterns"].find(query).skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

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

        rows.append({"id": cur["id"], "name": cur["name"], \
            "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3})

    return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}


def searchPatients(form, pageNum=1):

    rows = []
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

    numberTotalRows = mongoClient["patients"].count_documents(query)
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    cursor = mongoClient["patients"].find(query).skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    for cur in cursor:
        rows.append({"id": cur["id"], "name": cur["name"] , "surname1": cur["surname1"], \
            "surname2": cur["surname2"], "age": cur["age"]})

    return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}


def searchGroups(form, pageNum=1):

    rows = []
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
    numberTotalRows = mongoClient["groups"].count_documents(query)
    numberPages = math.ceil(numberTotalRows/rowsPerPage)
    
    cursor = mongoClient["groups"].find(query)

    for cur in cursor:
        description = ""
        if "description" in cur:
            description = cur["description"]
        rows.append({"id": cur["id"], "name": cur["name"] , "description": description})

    return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}


def searchGroupsPattern(idPattern, pageNum=1, outputFormat="arr"):
    numberTotalRows = mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "patterns" :idPattern})
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""
    
    cursorGroups = mongoClient["groups"].find({"therapist":current_user.get_id(), "patterns" :idPattern})\
        .skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    for cur in cursorGroups:
        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"]})
        else:
            rows += "{},{};".format(cur["id"], cur["name"])

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

        return rows


def searchPatternsPatient(idPatient, pageNum=1, outputFormat="arr"):
    cursorPatient = mongoClient["patients"].find_one({"id":idPatient})

    numberTotalRows = len(cursorPatient["patterns"])
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""

    cursorPatterns = mongoClient["patterns"].find({"therapist":current_user.get_id(), \
        "id" :{"$in": cursorPatient["patterns"]}}).skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    for cur in cursorPatterns:
        intensity1 = "Sí" if 1 in cur["intensities"] else "No"
        intensity2 = "Sí" if 2 in cur["intensities"] else "No"
        intensity3 = "Sí" if 3 in cur["intensities"] else "No"

        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"], "description":cur["description"], \
                "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3})
        else:
            rows += "{},{},{},{},{};".format(cur["id"], cur["name"], intensity1, intensity2, intensity3)

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

        return rows

def searchGroupsPatient(idPatient, pageNum=1, outputFormat="arr"):
    numberTotalRows = mongoClient["groups"].count_documents({"therapist":current_user.get_id(), \
        "patients" :idPatient})
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""

    cursorGroups = mongoClient["groups"].find({"therapist":current_user.get_id(), "patients" : idPatient})\
        .skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    for cur in cursorGroups:
        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"]})
        else:
            rows += "{},{};".format(cur["id"], cur["name"])

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

        return rows


def searchPatientsPattern(idPattern, pageNum=1, outputFormat="arr"):
    numberTotalRows = mongoClient["patients"].count_documents({"therapist":current_user.get_id(), \
        "patterns" :idPattern})
    numberPages = math.ceil(numberTotalRows/rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""
    
    cursorPatients = mongoClient["patients"].find({"therapist":current_user.get_id(), "patterns" :idPattern})\
        .skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    for cur in cursorPatients:
        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"], "surname1":cur["surname1"], "surname2":cur["surname2"], \
                "gender":cur["gender"], "age": cur["age"]})
        else:
            rows += "{},{},{},{},{},{};".format(cur["id"], cur["name"], cur["surname1"], cur["surname2"], \
                cur["gender"], cur["age"])

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

        return rows


def searchPatientsGroup(idGroup, pageNum=1, outputFormat="arr"):
    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id":idGroup})
    patientsAll = cursorGroup["patients"]
    patientsAll.sort()
    patientIds = patientsAll[(pageNum-1)*rowsPerPage : pageNum*rowsPerPage]
    numberTotalRows = len(patientsAll)
    numberPages = numberPages = math.ceil(numberTotalRows/rowsPerPage)
    
    cursorPatients = mongoClient["patients"].find({"therapist":current_user.get_id(), "id" : {"$in": patientIds}})\
        .skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""

    for cur in cursorPatients:
        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"], "surname1":cur["surname1"], "surname2":cur["surname2"], \
                "gender":cur["gender"], "age": cur["age"]})
        else:
            rows += "{},{},{},{},{},{};".format(cur["id"], cur["name"], cur["surname1"], cur["surname2"], \
                cur["gender"], cur["age"])

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

    return rows



def searchPatternsGroup(idGroup, pageNum=1, outputFormat="arr"):
    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id":idGroup})
    patternsAll = cursorGroup["patterns"]
    patternsAll.sort()
    patternsIds = patternsAll[(pageNum-1)*rowsPerPage : pageNum*rowsPerPage]
    numberTotalRows = len(patternsAll)
    numberPages = numberPages = math.ceil(numberTotalRows/rowsPerPage)
    
    cursorPatterns = mongoClient["patterns"].find({"therapist":current_user.get_id(), "id" : {"$in": patternsIds}})\
        .skip((pageNum-1)*rowsPerPage).limit(rowsPerPage)

    if outputFormat == "arr":
        rows = []
    else:
        rows = ""

    for cur in cursorPatterns:
        intensity1 = "Sí" if 1 in cur["intensities"] else "No"
        intensity2 = "Sí" if 2 in cur["intensities"] else "No"
        intensity3 = "Sí" if 3 in cur["intensities"] else "No"

        if outputFormat == "arr":
            rows.append({"id":cur["id"], "name":cur["name"], \
                "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3})
        else:
            rows += "{},{},{},{},{};".format(cur["id"], cur["name"], \
                intensity1, intensity2, intensity3)

    if outputFormat == "arr":
        return {"numberTotalRows":numberTotalRows, "numberPages":numberPages, "rows":rows}
    else:
        if len(rows) > 0 and rows[-1] == ";":
            rows = rows[:-1]

    return rows


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

def getEpisodesCursor(timestampFrom, timestampTo, idPatient, skip=0, limit=1000):
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
      },
      {
        "$skip": skip
      },
      {
        "$limit": limit
      }
    ])

    return cursor


def getCountMultipleEpisodes(timestampFrom, timestampTo, idPatient):
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

    return len(list(cursor))



def getMultipleEpisodes(timestampFrom, timestampTo, idPatient, pageNumber):
    result = []
    
    skip = (pageNumber-1)*rowsPerPage

    cursor = getEpisodesCursor(timestampFrom, timestampTo, idPatient, skip, rowsPerPage)

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
    rows = []
    cursor = getEpisodesCursor(timestampFrom, timestampTo, idPatient)

    firstRow = True
    valueFirstRow = {}
    valueLastTimestamp = 0
    valueLastRow = {}

    for episode in cursor:
        for alert in episode["v"]:
            #Insert preceeding zero alert state
            if firstRow:
                currentDate = datetime.fromtimestamp(int(alert["tmstamp"])-5)
                valueFirstRow = {"plotDate": currentDate.strftime("Date.UTC(%Y, %m, %d, %H, %M, %S)"), \
                "alertLevel": 0}
                firstRow = False
            else:
                valueLastTimestamp = int(alert["tmstamp"])
        
            currentDate = datetime.fromtimestamp(int(alert["tmstamp"]))
            rows.append({"plotDate": currentDate.strftime("Date.UTC(%Y, %m, %d, %H, %M, %S)"), \
                "date": currentDate.strftime("%d/%m/%Y"), "time": currentDate.strftime("%H:%M:%S"), \
                "alertLevel": alert["value"]})

    #Insert succeeding zero alert state
    currentDate = datetime.fromtimestamp(valueLastTimestamp+5)
    valueLastRow = {"plotDate": currentDate.strftime("Date.UTC(%Y, %m, %d, %H, %M, %S)"), "alertLevel": 0}

    rows.insert(0, valueFirstRow)
    rows.insert(len(rows), valueLastRow)
    
    return rows

def generateUniqueRandom(collection, field):
    token = ''.join(random.choice('0123456789ABCDEF') for i in range(6))

    while mongoClient[collection].find({field:token}).count() > 0:
        generateUniqueRandom(token)

    return token


def updatePattern(form, therapistId):
    idPattern = int(form.patternId.data)

    #Update patients which are no longer linked with the current pattern
    cursor = mongoClient["patients"].find({"therapist":therapistId, "patterns":idPattern, \
        "id":{"$nin": list(map(int, form.patients.data))}})

    for cur in cursor:
        mongoClient["patients"].update({"id":cur["id"]}, {"$pull": {"patterns":idPattern}})

    #Update groups which are no longer linked with the current pattern
    cursor = mongoClient["groups"].find({"therapist":therapistId, "patterns":idPattern, \
        "id":{"$nin": list(map(int, form.patients.data))}})

    for cur in cursor:
        mongoClient["groups"].update({"id":cur["id"]}, {"$pull": {"patterns":idPattern}})

    #Update patients which are now linked with the current pattern
    cursor = mongoClient["patients"].find({"therapist":therapistId, "patterns": {"$ne": idPattern}, \
        "id":{"$in": list(map(int, form.patients.data))}})

    for cur in cursor:
        mongoClient["patients"].update({"id":cur["id"]}, {"$push": {"patterns":idPattern}})

    #Update groups which are now linked with the current pattern
    cursor = mongoClient["groups"].find({"therapist":therapistId, "patterns": {"$ne": idPattern}, \
        "id":{"$in": list(map(int, form.groups.data))}})

    for cur in cursor:
        mongoClient["groups"].update({"id":cur["id"]}, {"$push": {"patterns":idPattern}})

    #Update the information of the pattern itself

    intensities = []

    if form.intensity1.data:
        intensities.append(1)

    if form.intensity2.data:
        intensities.append(2)

    if form.intensity3.data:
        intensities.append(3)

    #Update the pattern info
    mongoClient["patterns"].update_one({"id" : idPattern}, {"$set" : {"name" : form.name.data, \
        "description" : form.description.data, "intensities" : intensities}})


def updateGroup(form, therapistId, idGroup):
    cursorGroupOld = mongoClient["groups"].find_one({"id" : idGroup})

    oldPatients = cursorGroupOld["patients"]
    oldPatterns = cursorGroupOld["patterns"]

    newPatients = list(map(int, form.patients.data))
    newPatterns = list(map(int, form.patterns.data))

    discardedPatients = list(set(cursorGroupOld["patients"]) - set(newPatients))
    discardedPatterns = list(set(cursorGroupOld["patterns"]) - set(newPatterns))

    #Old patients that remain linked to the group
    oldNewPatients = list(set(oldPatients) & set(newPatients))

    #1. Delete all old patterns from all old discarded patients
    for idPattern in oldPatterns:
        mongoClient["patients"].update_many({"id":{"$in":discardedPatients}}, {"$pull": {"patterns":idPattern}})

    #2. Delete all old discarded patterns from old patients not discarded
    for idPattern in discardedPatterns:
        mongoClient["patients"].update_many({"id":{"$in":oldNewPatients}}, {"$pull": {"patterns":idPattern}})

    #3. Add new patterns to all new patients
    for idPattern in newPatterns:
        mongoClient["patients"].update_many({"id":{"$in":newPatients}}, {"$push": {"patterns":idPattern}})

    #4. Update group info
    mongoClient["groups"].update_one({"id" : idGroup}, {"$set" : {"name": form.name.data, \
        "description": form.description.data, "patients": newPatients, "patterns": newPatterns }})
