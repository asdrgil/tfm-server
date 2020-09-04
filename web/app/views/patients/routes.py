from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from app import db
from app.mongoMethods import searchPatterns, generateUniqueRandom, searchPatients, getMultipleEpisodes, \
    getCountMultipleEpisodes, getOneEpisode, searchPatternsPatient, getEpisodes, registerTraceUsers
from app.views.patients import bp
from app.constants import mongoClient, urlPrefix, registerTokenLength, communicationTokenLength
from app.forms import RegisterPatternForm, SearchPatternsForm, PaginationForm, RegisterPatientForm, EditPatientForm, \
    GenericEditForm, FilterByDateForm, SearchPatientsForm

from datetime import datetime
import time
import math

therapistLiteral = ""

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        registerTraceUsers(current_user.get_id(), request.endpoint)

        global therapistLiteral

        therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
            current_user.get_surname2())
    else:
        #Trace for users is not added here because it will be spotted when redirecting the user
        return redirect(urlPrefix + url_for('auth.login'))

@login_required
@bp.route('/registrarPautaPaciente/<int:idPatient>', methods=['GET', 'POST'])
def registerPatternPatient(idPatient):
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe el paciente especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    form = RegisterPatternForm(current_user.get_id())

    cursorPatient = mongoClient["patients"].find_one({"id": idPatient})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient) , "name": cursorPatient["name"] + " " + cursorPatient["surname1"]}]

    if form.validate_on_submit():

        form.name.data = form.name.data.strip()

        #The patternName must be univoque
        if mongoClient["patterns"].count_documents({"therapist": current_user.get_id(), "name":form.name.data}) == 0:

            cursor = mongoClient["patterns"].find({}).sort("id",-1).limit(1)
            
            #idPattern is incremental and univoque
            idPattern = 1
            for cur in cursor:
                idPattern = cur["id"] + 1

            mongoClient["patients"].update_one({"id" : idPatient}, {"$push": {"patterns":idPattern}})
            
            cursor = mongoClient["patients"].find_one({"id" : idPatient})
            communicationToken = cursor["communicationToken"]
            
            if mongoClient["updatePatternsAndroid"].count_documents({"communicationToken":communicationToken, "operation":"add"}) == 0:
                mongoClient["updatePatternsAndroid"].insert_one({"communicationToken":communicationToken, "operation":"add", "patterns":[idPattern]})
            else:
                mongoClient["updatePatternsAndroid"].update_one({"communicationToken":communicationToken, "operation":"add"}, {"$push":{"patterns":idPattern}})

            #Add intensities
            intensities = []

            if form.intensity1.data:
                intensities.append(1)

            if form.intensity2.data:
                intensities.append(2)

            if form.intensity3.data:
                intensities.append(3)                

            mongoClient["patterns"].insert_one({"therapist":current_user.get_id(), "id":idPattern, \
                'name': form.name.data, 'description': form.description.data.strip(), 'intensities': intensities})

            flash("Pauta creada correctamente.", "success")
            return redirect(urlPrefix + url_for('patients.viewPatient', idPatient=idPatient))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")

    form = RegisterPatternForm(current_user.get_id())

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    return render_template('patients/registerPatternPatient.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral, patientInfo=patientInfo, rowsBreadCrumb=rowsBreadCrumb)


@login_required
@bp.route('/enlazarPautasPaciente/<int:idPatient>', methods=['GET', 'POST'])
def linkPatternsPatient(idPatient):
    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    cursorPatient = mongoClient["patients"].find_one({"therapist":current_user.get_id(), "id": idPatient})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient), "name": cursorPatient["name"] + " " + cursorPatient["surname1"]}]


    #Link patterns to patient
    if request.args.get("pattIds") is not None:
        pattIds = list(map(int, request.args.get("pattIds").split(",")))
        mongoClient["patients"].update_one({"id":idPatient}, {"$push": {"patterns":{"$each" : pattIds}} })
        flash("Pautas vinculadas al paciente correctamente", "success")

    if form.validate_on_submit() is False:
        form.name.data = ""
        form.patients.data = []
        form.groups.data = []
        form.intensities.data = []
        form.pageNumber.data = "1"

    queryResult = searchPatterns(form, int(form.pageNumber.data), {"type":"patients", "id":idPatient})
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('patients/linkPatternsPatient.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], patientInfo=patientInfo, rowsBreadCrumb=rowsBreadCrumb)


@login_required
@bp.route('/registrarPaciente', methods=['GET', 'POST'])
def registerPatient():
    form = RegisterPatientForm()

    #syncNow is always checked
    form.syncNow.data = True

    if form.validate_on_submit():

        #{name, surname1, surname2, gender, age} must be univoque
        if mongoClient["patients"].count_documents({"therapist":current_user.get_id(), "name": form.name.data, \
            "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data, \
            "gender": form.gender.data}) == 0:
            
            #Registration token that the user should introduce in the app    
            registrationToken = generateUniqueRandom("register", registerTokenLength)
            
            #Communication token that will be used to identify the user in the communications with the server
            communicationToken = generateUniqueRandom("communication", communicationTokenLength)

            #Delete all possible temporal registers of tryouts to register this same user as they are no longer usefull
            mongoClient["tmpPatientToken"].delete_many({'name': form.name.data, 'surname1': form.surname1.data, \
                'surname2': form.surname2.data, 'surname2': form.surname2.data, "gender": form.gender.data})

            mongoClient["tmpPatientToken"].insert_one({'id': registrationToken, 'synced': False, \
                "name": form.name.data, "surname1": form.surname1.data, "surname2": form.surname2.data, \
                "age": form.age.data, "gender": form.gender.data, "timestamp" : int(time.time()), \
                "communicationToken":communicationToken})
            form.registrationToken.data = registrationToken
        
        else:
            form.syncHidden.data = "False"
            flash("Ya existe un paciente con estos credenciales", "error")
    
    else:
        print("[DEBUG] form.errors: ")
        print(form.errors)
        
        form.syncHidden.data = "False"

        if form.name.data is None:
            form.name.data = ""
        
        if form.surname1.data is None:
            form.surname1.data = ""
        
        if form.surname2.data is None:
            form.surname2.data = ""
        
        if form.age.data is None:
            form.age.data = ""

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    return render_template('patients/registerPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)


@login_required
@bp.route('/modificarPaciente/<int:idPatient>', methods=['GET', 'POST'])
def modifyPatient(idPatient):
    form = RegisterPatientForm()

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient), "name": cursorPatient["name"] \
        + " " + cursorPatient["surname1"]}]

    if form.validate_on_submit():

        #{name, surname1, surname2, gender, age} must be univoque
        if mongoClient["patients"].count_documents({"therapist":current_user.get_id(), "name": form.name.data, \
            "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data, \
            "gender": form.gender.data, "id": {"$ne": idPatient}}) == 0:

            mongoClient["patients"].update_one({"id":idPatient}, {"$set": {"name": form.name.data, \
                "surname1": form.surname1.data, "surname2": form.surname2.data, \
                "age": int(form.age.data), "gender": form.gender.data}})

            flash("Paciente modificado correctamente", "success")
            return redirect(urlPrefix + url_for('patients.viewPatient', idPatient=idPatient))
        
        else:
            flash("Ya existe un paciente con estos credenciales", "error")
    
    else:

        form.name.data = cursorPatient["name"]
        form.surname1.data = cursorPatient["surname1"]
        form.surname2.data = cursorPatient["surname2"]
        form.age.data = int(cursorPatient["age"])
        form.gender.data = cursorPatient["gender"]

    return render_template('patients/modifyPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb, idPatient=idPatient)

@login_required
@bp.route('/verPaciente/<int:idPatient>/', methods=['GET', 'POST'])
def viewPatient(idPatient):
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente indicado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}
        
    #Link patterns to patient
    if request.args.get("linkPattIds") is not None:
        pattIds = list(map(int, request.args.get("linkPattIds").split(",")))
        print(pattIds)
        mongoClient["patients"].update_one({"id":idPatient}, {"$push": {"patterns":{"$each" : pattIds}} })
        
        cursor = mongoClient["patients"].find_one({"id" : idPatient})
        communicationToken = cursor["communicationToken"]
        
        if mongoClient["updatePatternsAndroid"].count_documents({"communicationToken":communicationToken, "operation":"add"}) == 0:
            mongoClient["updatePatternsAndroid"].insert_one({"communicationToken":communicationToken, "operation":"add", "patterns":pattIds})
        else:
            mongoClient["updatePatternsAndroid"].update_one({"communicationToken":communicationToken, "operation":"add"}, {"$push": {"patterns":{"$each" : pattIds}}})
        
        flash("Pautas vinculadas al paciente correctamente", "success")

    form = EditPatientForm(current_user.get_id())
    form2 = GenericEditForm()
    form3 = PaginationForm(1)
    form4 = FilterByDateForm(current_user.get_id(), 1)
    form5 = SearchPatternsForm(current_user.get_id())
    form6 = PaginationForm(1)
    
    if form5.validate_on_submit() is False:
        form5.name.data = ""
        form5.patients.data = []
        form5.groups.data = []
        form5.intensities.data = []
        form5.pageNumber.data = "1"

    #Set default values of filter by date form

    #FROM
    if form4.date1.data == None:
        form4.date1.data = "2000-01-01"
        form4.time1.data = "00:00"

    if form4.time1.data == None:
        form4.time1.data = "00:00"

    #TO
    if form4.date2.data == None:
        form4.date2.data = "2050-01-01"
        form4.time2.data = "23:59"

    if form4.time2.data == None:
        form4.time2.data = "23:59"    

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}]

    #Unlink pattern
    if request.args.get("unlinkPatt") is not None:
        unlinkPatt = int(request.args.get("unlinkPatt"))
        
        mongoClient["patients"].update_one({"id":idPatient}, {"$pull": \
            {"patterns": unlinkPatt}})
        
        cursor = mongoClient["patients"].find_one({"id" : idPatient})
        communicationToken = cursor["communicationToken"]        
        
        if mongoClient["updatePatternsAndroid"].count_documents({"communicationToken":communicationToken, "operation":"delete"}) == 0:
            mongoClient["updatePatternsAndroid"].insert_one({"communicationToken":communicationToken, "operation":"delete", "patterns":[unlinkPatt]})
        else:
            mongoClient["updatePatternsAndroid"].update_one({"communicationToken":communicationToken, "operation":"delete"}, {"$push":{"patterns":unlinkPatt}})


    cursorPatient = mongoClient["patients"].find_one({"id":idPatient})
    
    #Get patient's patterns
    queryResultPatterns = searchPatternsPatient(idPatient, 1, "arr")

    #Get episodes from the patient
    #TODO: check if the 4 params of time should be "". Probably form4 should be passed as param
    rowEpisodes, numberRowsEpisodes, pagesEpisodes = getEpisodes(idPatient, "", "", "", "")
    
    queryResultLinkPatt = searchPatterns(form5, int(form5.pageNumber.data), {"type":"patients", "id":idPatient})
    form6 = PaginationForm(queryResultLinkPatt["numberPages"])
    form6.pagination.data = form5.pageNumber.data   

    return render_template('patients/viewPatient.html', therapistLiteral=therapistLiteral, \
        rowsPatterns=queryResultPatterns["rows"], form=form, form2=form2, \
        form3=form3, form4=form4, form5=form5, form6=form6, \
        pagesPatterns=queryResultPatterns["numberPages"], \
        numberRowsPattern=queryResultPatterns["numberTotalRows"], rowsBreadCrumb=rowsBreadCrumb, \
        patientInfo=patientInfo, rowEpisodes=rowEpisodes, numberRowsEpisodes=numberRowsEpisodes, \
        pagesEpisodes=pagesEpisodes, rowLinkPatt=queryResultLinkPatt["rows"], \
        numberTotalRowsLinkPatt=queryResultLinkPatt["numberTotalRows"], \
        numberPagesLinkPatt=queryResultLinkPatt["numberPages"])


@login_required
@bp.route('/verPacientes', methods=['GET', 'POST'])
def viewPatients():
    form = SearchPatientsForm(current_user.get_id())
    form2 = PaginationForm(1)

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    if request.args.get('deleteElem') is not None:
        mongoClient["patients"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Paciente eliminado correctamente", "info")

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.surname1.data = ""
        form.surname2.data = ""
        form.age.data = ""
        form.pageNumber.data = 1
        form.patterns.data = ""
        form.genders.data = ""

    queryResult = searchPatients(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('patients/viewPatients.html', form=form, form2=form2, \
        rowPatients=queryResult["rows"], therapistLiteral=therapistLiteral, \
        numberTotalRows=queryResult["numberTotalRows"], numberPages=queryResult["numberPages"], \
        rowsBreadCrumb=rowsBreadCrumb)


'''
@login_required
@bp.route('/verEpisodios/<int:idPatient>', methods=['GET', 'POST'])
def viewEpisodes(idPatient):

    if idPatient is not 0 and mongoClient["patients"].count_documents({"id":idPatient, \
        "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    cursorPatient = mongoClient["patients"].find_one({"therapist":current_user.get_id(), "id": idPatient})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}    

    form = FilterByDateForm(current_user.get_id(), 1)
    form.submitDone.data = 0
    numberPages = 0

    if form.validate_on_submit():

        form.submitDone.data = 1

        pageNumber = 1 if form.pagination.data == str(None) else int(form.pagination.data)

        #FROM
        if len(form.date1.data) == 0:
            form.date1.data = "2000-01-01"
            form.time1.data = "00:00"

        if len(form.time1.data) == 0:
            form.time1.data = "00:00"

        #TO
        if len(form.date2.data) == 0:
            form.date2.data = "2050-01-01"
            form.time2.data = "23:59"

        if len(form.time2.data) == 0:
            form.time2.data = "23:59"

        timestampTo = 0

        timestampFrom = int(datetime.strptime('{} {}'.format(form.date1.data, form.time1.data), '%Y-%m-%d %H:%M')\
            .strftime("%s"))
        timestampTo = int(datetime.strptime('{} {}'.format(form.date2.data, form.time2.data), '%Y-%m-%d %H:%M')\
            .strftime("%s"))

        rowEpisodes = getMultipleEpisodes(timestampFrom, timestampTo, idPatient, pageNumber)
        numberTotalRows = getCountMultipleEpisodes(timestampFrom, timestampTo, idPatient)
        numberPages = math.ceil(numberTotalRows/rowsPerPage)

        return render_template('patients/viewEpisodes.html', form=form, therapistLiteral=therapistLiteral, \
            patientInfo=patientInfo, rowEpisodes=rowEpisodes, numberTotalRows=numberTotalRows, numberPages=numberPages)

    return render_template('patients/viewEpisodes.html', form=form, therapistLiteral=therapistLiteral, patientInfo=patientInfo)
'''

@bp.route('/verUnEpisodio', methods=['GET', 'POST'])
@login_required
def viewOneEpisode():
    if request.args.get('idPatient') is None or \
        request.args.get('timestampFrom') is None or request.args.get('timestampTo') is None:
        flash("Es necesario especificar el paciente y el intervalo temporal", "error")

    idPatient = int(request.args.get('idPatient'))

    if mongoClient["patients"].count_documents({"id":idPatient, "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist": current_user.get_id()})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}


    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient), "name": cursorPatient["name"] + " " + cursorPatient["surname1"]}]    

    timestampFrom = int(request.args.get('timestampFrom'))
    timestampTo = int(request.args.get('timestampTo'))

    rowEpisodes = getOneEpisode(timestampFrom, timestampTo, idPatient)

    return render_template('patients/viewOneEpisode.html', rowEpisodes=rowEpisodes, therapistLiteral=therapistLiteral, \
        rowsBreadCrumb=rowsBreadCrumb, patientInfo=patientInfo)
