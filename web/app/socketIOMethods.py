from flask_socketio import emit
from app import socketio, thread_lock
from .mongoMethods import deletePattern, insertPatternTmp, getPatternsSelectPattern, \
    getPatternsSelectGroup, insertPatient, getUnlinkPattern, searchGroupsPattern, searchPatientsPattern, \
    searchPatientsGroup, searchPatternsGroup, searchPatternsPatient, viewEpisodes
from .constants import mongoClient, counterSleepTmp


################  editPattern ##################

@socketio.on('deletePatternEv', namespace='/editPattern')
def editPatternSocket(message):
    deletePattern(message)
    emit("deleted", '')

################ registerPatient & editPatient ################

@socketio.on('insertNewPattern', namespace='/editPatient')
@socketio.on('insertNewPattern', namespace='/registerGroup')
@socketio.on('insertNewPattern', namespace='/editGroup')
def insertNewPattern(message):
    body, error = insertPatternTmp(message)
    emit("getPatterns", {'body': body, "error": error})

#Event that fires onChange event of selectPattern
@socketio.on('changedSelectPattern', namespace='/editPatient')
@socketio.on('changedSelectPattern', namespace='/registerGroup')
@socketio.on('changedSelectPattern', namespace='/editGroup')
def changedSelectPattern(message):
    print("[DEBUG] message:")
    print(message)
    body = getPatternsSelectPattern(message)
    emit("getPatterns", {'body': body, "error": ""})

#Event that fires onChange event of selectGroup
@socketio.on('changedSelectGroup', namespace='/editPatient')
def changedSelectGroup(message):
    body = getPatternsSelectGroup(message)
    emit("getPatterns", {'body': body, "error": ""})


def background_thread(registrationToken, windowToken):

    while mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) == 1:
        socketio.sleep(1)

    #If a token has been marked as synced, redirect to index. If not, the user has pressed cancel
    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': True}) == 1:
        cursorRegistrationToken = mongoClient["tmpPatientToken"].find_one({'id': registrationToken})
        insertPatient(windowToken, cursorRegistrationToken["name"], cursorRegistrationToken["surname1"], \
            cursorRegistrationToken["surname2"], cursorRegistrationToken["age"], cursorRegistrationToken["gender"], \
            cursorRegistrationToken["groups"], True)
        mongoClient["tmpPatientToken"].delete_one({'id': registrationToken})

        socketio.emit('redirect',
          namespace='/registerPatient')



#Event that fires after submitting the formularie
@socketio.on('registerPatientEvent', namespace='/registerPatient')
def registerPatientEvent(message):
    registrationToken = message["registrationToken"]
    windowToken = message["windowToken"]
    global thread
    with thread_lock:
    #if thread is None:
        thread = socketio.start_background_task(background_thread, registrationToken, windowToken)


#Event that fires onChange event of selectPattern
@socketio.on('unlinkPattern', namespace='/registerPatient')
@socketio.on('unlinkPattern', namespace='/editPatient')
@socketio.on('unlinkPattern', namespace='/registerGroup')
@socketio.on('unlinkPattern', namespace='/editGroup')
def unlinkPattern(message):
    body = getUnlinkPattern(message)
    
    emit("getPatterns", {'body': body, "error": ""})




#Event that fires onChange event of selectGroup
@socketio.on('paginationGroup', namespace='/viewPattern')
def paginationGroupViewPattern(message):
    body = searchGroupsPattern(int(message["idPattern"]), int(message["groupPage"]), "str")
    emit("paginationGroup", {'body': body, "error": ""})


@socketio.on('paginationPattern', namespace='/viewGroup')
def paginationPatternViewPattern(message):
    body = searchPatternsGroup(int(message["idGroup"]), int(message["patternPage"]), "str")
    emit("paginationPattern", {'body': body, "error": ""})


@socketio.on('paginationPatient', namespace='/viewPattern')
def paginationPatientViewPattern(message):
    body = searchPatientsPattern(int(message["idPattern"]), int(message["patientPage"]), "str")
    print("[DEBUG] body:")
    print(body)

    emit("paginationPatient", {'body': body, "error": ""})


@socketio.on('paginationPattern', namespace='/viewPatient')
def paginationPatternViewPatient(message):
    body = searchPatternsPatient(int(message["idPatient"]), int(message["patternPage"]), "str")
    emit("paginationPattern", {'body': body, "error": ""})


@socketio.on('episodes', namespace='/viewPatient')
def episodesViewPatient(message):
    print("[DEBUG] INN.")

    rowEpisodes, numberTotalRows, numberPages = viewEpisodes(int(message["idPatient"]), message["date1"], message["time1"], \
        message["date2"], message["time2"])
    
    emit("episodes", {'rowEpisodes': rowEpisodes, "numberTotalRows": numberTotalRows, "numberPages":numberPages})


@socketio.on('linkPatternsPatient', namespace='/linkPatternsPatient')
def linkPatternsPatient(message):

    patternIds = message["patterns"].split(",")

    for patt in patternIds:
        mongoClient["patients"].update_one({"id":message["idPatient"]}, { "$addToSet": {"patterns": int(patt)}})


@socketio.on('linkPatientsPattern', namespace='/linkPatientsPattern')
def linkPatientsPattern(message):

    patientIds = message["patients"].split(",")

    for pati in patientIds:
        mongoClient["patients"].update_one({"id":int(pati)}, { "$push": {"patterns": int(idPattern)}})        


@socketio.on('unlinkPattern', namespace='/viewPatient')
def unlinkPatternPatient(message):
    #mongoClient["patients"].update_one({"id":message["idPatient"]}, { "$pull": {"patterns": message["pattern"]}})
    #DEBUG: todo: update the cookie viewPatientPatterns-idPatient in order to set the given pattern as unlinked.
    #Then, refresh the page to view the changes

    data = ""

    if mongoClient["session"].count_documents({"id": "viewPatientPatterns-" + str(message["idPatient"])}) == 0:
        data = "||" + str(message["pattern"])
    else:
        cursorSession = mongoClient["session"].find_one({"id": "viewPatientPatterns-" + str(message["idPatient"])})
        dataArr = cursorSession["data"].replace(str(message["pattern"]), "").replace(",,",",").split("|")
        
        if len(dataArr[2]) == 0:
            dataArr[2] = str(message["pattern"])
        else:
            dataArr[2] += "," + str(message["pattern"])

        data = dataArr[0] + "|" + dataArr[1] + "|" + dataArr[2]

        mongoClient["session"].delete_one({"id": "viewPatientPatterns-" + str(message["idPatient"])})

    mongoClient["session"].insert_one({"id": "viewPatientPatterns-" + str(message["idPatient"]), "data":data})

@socketio.on('cookiePatientInfo', namespace='/viewPatient')
def cookiePatientInfo(message):
    data = "{},{},{},{},{}".format\
        (message["name"], message["surname1"], message["surname2"], message["age"], message["gender"])

    mongoClient["session"].delete_one({"id": "viewPatientInfo-" + str(message["idPatient"])})
    mongoClient["session"].insert_one({"id": "viewPatientInfo-" + str(message["idPatient"]), "data": data})
    

def removeTmpViewPatient(idPatient):

    while mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) == 1:
        socketio.sleep(1)

    #If a token has been marked as synced, redirect to index. If not, the user has pressed cancel
    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': True}) == 1:
        cursorRegistrationToken = mongoClient["tmpPatientToken"].find_one({'id': registrationToken})
        insertPatient(windowToken, cursorRegistrationToken["name"], cursorRegistrationToken["surname1"], \
            cursorRegistrationToken["surname2"], cursorRegistrationToken["age"], cursorRegistrationToken["gender"], \
            cursorRegistrationToken["groups"], True)
        mongoClient["tmpPatientToken"].delete_one({'id': registrationToken})

        socketio.emit('redirect',
          namespace='/registerPatient')

# Function to know if the screen was opened in the last 4 minutes. If not, discard all temporal changes
# from the given patient
@socketio.on('ping', namespace='/viewPatient')
def pingViewPatient(message):
    t1 = threading.Thread(target=pingPatientBackground, args=(counterSleepTmp))
    t1.start()
    t1.join()

    mongoClient["session"].delete_one({"id": "viewPatientInfo-" + str(message["idPatient"])})
    mongoClient["session"].insert_one({"id": "viewPatientInfo-" + str(message["idPatient"]), "data": data})

################################