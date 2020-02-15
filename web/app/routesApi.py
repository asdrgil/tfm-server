from app import app
from flask import jsonify
from .constants import mongoClient, tokenLength

@app.route('/api/v1/sincronizarDispositivo/<registrationToken>', methods=['GET'])
def syncDevice(registrationToken):
    if len(registrationToken) is not tokenLength:
        #abort(404)
        jsonify({'code': -1, "message":"El token introducido debe tener una longitud de seis caracteres."})

    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) > 0:
        mongoClient["tmpPatientToken"].update_one({'id': registrationToken}, {"$set": {'synced': True}})
        return jsonify({'code': 0, "message":u"Paciente sincronizado correctamente."})
    
    elif mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': True}) > 0:
        return jsonify({'code': 1, "message":u"El token introducido ya ha sido usado por otro paciente."})
    
    else:
        return jsonify({'code': 2, "message":u"El token introducido no es correcto."})

@app.route('/api/v1/sincronizarDispositivo/<registrationToken>', methods=['GET'])