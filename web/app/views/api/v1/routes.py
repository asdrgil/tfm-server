from flask import jsonify
#from flask_login import login_required
from app import db
from app.constants import mongoClient, tokenLength
from app.views.api.v1 import bp

#@login_required
@bp.route('/api/v1/sincronizarDispositivo/<registrationToken>', methods=['GET', 'POST'])
def syncDevice(registrationToken):
    #Request.get registrationToken

    if len(registrationToken) is not tokenLength:
        #abort(404)
        return jsonify({'code': -1, "message":"El token introducido debe tener una longitud de seis caracteres."})

    if mongoClient["tmpPatientToken"].count_documents({'id': registrationToken, 'synced': False}) > 0:
        mongoClient["tmpPatientToken"].update_one({'id': registrationToken}, {"$set": {'synced': True}})
        return jsonify({'code': 1, "message":u"Paciente sincronizado correctamente."})
    else:
        return jsonify({'code': 3, "message":u"El token introducido no es correcto."})
