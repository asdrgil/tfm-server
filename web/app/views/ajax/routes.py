from flask import render_template, jsonify, request
from app.constants import mongoClient
from app.mongoMethods import insertPatient, getEpisodes
from app.views.ajax import bp
import time

#########################################################
##### Positive code numbers: everything went OK.    #####
##### Negative code numbers: error found.           #####
##### Default code number when everything is OK: 1. #####
#########################################################

@bp.route('/ajax/registrarpaciente/<registrationToken>', methods=['GET', 'POST'])
def ajaxRegisterPatient(registrationToken):

    #Invalid token
    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken}) == 0:
        return jsonify({'code': -1, "message":"El código del paciente introducido no es válido."})
    
    #Token already used
    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) == 1:
        return jsonify({'code': -2})
    #Valid token and not used (synced at this moment)
    else:
        cursorPatient = mongoClient["tmpPatientToken"].find_one({'id': registrationToken})
        insertPatient(cursorPatient["name"], cursorPatient["surname1"], cursorPatient["surname2"], \
            cursorPatient["age"], cursorPatient["gender"], cursorPatient["communicationToken"]) #Communication token

        mongoClient["tmpPatientToken"].delete_one({'id': registrationToken})
        return jsonify({'code': 1})


@bp.route('/ajax/episodiosPaciente/<int:idPatient>', methods=['GET', 'POST'])
def ajaxEpisodesPatient(idPatient):

    #Check if all the arguments where passed
    if request.args.get("date1") == None or request.args.get("time1") == None or request.args.get("date2") == None \
        or request.args.get("time2") == None:
        return jsonify({'code': -1})

    rowEpisodes, numberTotalRows, numberPages = getEpisodes(idPatient, request.args.get("date1"), \
        request.args.get("time1"), request.args.get("date2"), request.args.get("time2"))

    return jsonify({"code": 1, \
        "episodes": {'rowEpisodes': rowEpisodes, "numberTotalRows": numberTotalRows, "numberPages":numberPages}})
