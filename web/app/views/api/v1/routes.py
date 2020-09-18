from flask import jsonify
#from flask_login import login_required
from app import db
from app.constants import mongoClient, registerTokenLength, communicationTokenLength
from app.views.api.v1 import bp
from app.mongoMethods import getUpdatePatternsAndroid, parseEpisodes
from flask import request
import json


@bp.route('/api/v1/sincronizarDispositivo/<registrationToken>', methods=['GET', 'POST'])
def syncDevice(registrationToken):
    #Request.get registrationToken

    if len(registrationToken) is not registerTokenLength:
        #abort(404)
        return jsonify({'code': -1, "message":"El token introducido debe tener una longitud de seis caracteres."})

    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) > 0:
        mongoClient["tmpPatientToken"].update_one({'id': registrationToken}, {"$set": {'synced': True}})
        cursorPatient = mongoClient["tmpPatientToken"].find_one({'id': registrationToken})
            
        return jsonify({'code': 1, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
            "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"], \
            "communicationToken":cursorPatient["communicationToken"]})
    else:
        return jsonify({'code': -2, "message":u"El token introducido no es correcto."})



@bp.route('/api/v1/histEstadoPaciente/<communicationToken>', methods=['GET', 'POST'])
def histPatientState(communicationToken):
    parseEpisodes(communicationToken, json.loads(request.data.decode('utf8')))

    #TODO
    return jsonify({'code': 1, "message":u"Tryout."})

@bp.route('/api/v1/actualizarPautasPaciente/<communicationToken>', methods=['GET', 'POST'])
def updatePatternsPatient(communicationToken):
    if len(communicationToken) is not communicationTokenLength or \
        mongoClient["patients"].count_documents({"communicationToken":communicationToken}) == 0:
        return jsonify({'code': -1, "message":"El token introducido no es válido."})
        
    if mongoClient["updatePatternsAndroid"].count_documents({"communicationToken":communicationToken}) == 0:
        return jsonify({'code': 0, "message":"No hay cambios pendientes"})
        
    result = {}
    
    operations = ['add', 'modify', 'delete']
    
    for operation in operations:
        if mongoClient["updatePatternsAndroid"].count_documents({"communicationToken":communicationToken, "operation":operation}) > 0:
            result[operation] = []
        
        cursor = getUpdatePatternsAndroid(operation, communicationToken)
            
        for cur in cursor:
            dict_data = {
                'idPattern':cur["id"],
                'name': cur["name"],
                'intensities': cur["intensities"],
            }

            result[operation].append(dict_data)
            
        mongoClient["updatePatternsAndroid"].delete_many({"communicationToken":communicationToken})
            
    return jsonify(result)
