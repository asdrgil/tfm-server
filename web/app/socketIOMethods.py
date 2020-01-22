from flask_socketio import SocketIO, emit
from app import app, db, socketio, thread_lock, thread
from pymongo import MongoClient, errors
from .mongoMethods import deletePattern, insertPatternTmp, getTmpPatterns, getPatternsSelectPattern, \
    getPatternsSelectGroup, insertPatient, getUnlinkPattern, searchGroupsPattern, searchPatientsPattern, \
    searchPatientsGroup, searchPatternsGroup, searchPatternsPatient, searchGroupsPatient, viewEpisodes
from datetime import datetime

#Constants
mongoClient = MongoClient('localhost:27017').tfm

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



@socketio.on('paginationPatient', namespace='/viewGroup')
def paginationGroupViewPattern(message):
    body = searchPatientsGroup(int(message["idGroup"]), int(message["patientPage"]), "str")

    emit("paginationPatient", {'body': body, "error": ""})


@socketio.on('paginationPattern', namespace='/viewPatient')
def paginationPatternViewPatient(message):
    body = searchPatternsPatient(int(message["idPatient"]), int(message["patternPage"]), "str")
    emit("paginationPattern", {'body': body, "error": ""})


@socketio.on('episodes', namespace='/viewPatient')
def episodesViewPatient(message):
    rowEpisodes, numberTotalRows, numberPages = viewEpisodes(int(message["idPatient"]), message["date1"], message["time1"], \
        message["date2"], message["time2"])
    
    emit("episodes", {'rowEpisodes': rowEpisodes, "numberTotalRows": numberTotalRows, "numberPages":numberPages})


################################