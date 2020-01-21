from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db, socketio, thread_lock, thread
from app.forms import LoginForm, RegisterTherapistForm, RegisterPatientForm, RegisterPatternForm, \
    RegistrationGroupForm, EditPatternForm, SearchPatternsForm, SearchPatientsForm, SearchGroupsForm, EditPatientForm, \
    RegisterPatternForm2, GenericEditForm, FilterByDateForm, TryoutForm, PaginationForm, PaginationForm2
from app.models import User
import random
from threading import Lock
from flask_socketio import SocketIO, emit, join_room, leave_room, \
close_room, rooms, disconnect
import sys
from bson.json_util import dumps
import string
from pymongo import MongoClient, errors
import json
import math
import datetime as dt
from datetime import datetime
from datetime import timedelta
from datetime import date
import time
from operator import itemgetter
from .socketIOMethods import editPatternSocket, changedSelectGroup, changedSelectPattern, registerPatientEvent, \
    insertNewPattern, getTmpPatterns
from .mongoMethods import searchPatterns, searchPatients, searchGroups, getMultipleEpisodes, getOneEpisode, \
    insertPatient, generateUniqueRandom, updatePattern, searchGroupsPattern, searchPatientsPattern, \
    searchPatientsGroup, searchPatternsGroup, updateGroup, searchGroupsPatient, searchPatternsPatient, \
    getCountMultipleEpisodes
from .constants import mongoClient, rowsPerPage

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/registrarTerapeuta', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash(u'Ya hay una sesión activa', 'info')
        return redirect(url_for('index'))

    form = RegisterTherapistForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)

        user.set_password(form.password.data)
        user.set_name(form.name.data)
        user.set_surname1(form.surname1.data)
        user.set_surname2(form.surname2.data)
        db.session.add(user)
        db.session.commit()

        flash(u'Terapeuta registrado correctamente', 'success')

        return redirect(url_for('iniciarSesion'))

    return render_template('registerTherapist.html', title='Registrar terapeuta', form=form)


@app.route('/iniciarSesion', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash(u'Ya hay una sesión activa', 'info')
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(u'Usuario o contraseña inválidos', 'error')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)
        flash(u'Has iniciado sesión correctamente', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', title='Iniciar sesión', form=form)


@app.route('/registrarPauta', methods=['GET', 'POST'])
@login_required
def registerPattern():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = RegisterPatternForm(current_user.get_id())

    if form.validate_on_submit():

        form.name.data = form.name.data.strip()

        #The patternName must be univoque
        if mongoClient["patterns"].count_documents({"therapist": current_user.get_id(), "name":form.name.data}) == 0:

            cursor = mongoClient["patterns"].find({}).sort("id",-1).limit(1)
            
            #idPattern is incremental and univoque
            idPattern = 1
            for cur in cursor:
                idPattern = cur["id"] + 1

            #Set pattern to patients
            for patientId in form.patients.data:
                mongoClient["patients"].update_one({"id" : int(patientId)}, {"$push": {"patterns":idPattern}})
            
            #Set pattern to groups
            for group in form.groups.data:
                mongoClient["groups"].update_one({"id" : int(group)}, {"$push": {"patterns":idPattern}})

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
            return redirect(url_for('index'))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")



    return render_template('registerPattern.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral)


@app.route('/editarPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def editPattern(idPattern):
    if mongoClient["patterns"].count_documents({"id":idPattern, "therapist":current_user.get_id()}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    
    form = EditPatternForm(current_user.get_id())
    form2 = GenericEditForm()

    if form.validate_on_submit():
        updatePattern(form, current_user.get_id())
        
        flash("Pauta modificada correctamente", "success")
        return redirect(url_for('index'))

    else:

        form.patternId.data = idPattern

        patternData = mongoClient["patterns"].find_one({"id":int(idPattern), "therapist":current_user.get_id()})
        cursorPatients = mongoClient["patients"].find({"patterns" :int(idPattern), "therapist":current_user.get_id()})
        cursorGroups = mongoClient["groups"].find({"patterns" :int(idPattern), "therapist":current_user.get_id()})

        form.name.data = patternData["name"]
        form.description.data = patternData["description"]

        if "intensities" in patternData:
            form.intensity1.data = 1 in patternData["intensities"]
            form.intensity2.data = 2 in patternData["intensities"]
            form.intensity3.data = 3 in patternData["intensities"]

        selectedPatients = []

        for cur in cursorPatients:
            selectedPatients.append(str(cur["id"]))

        selectedGroups = []

        for cur in cursorGroups:
            selectedGroups.append(str(cur["id"]))

        form.patients.data = selectedPatients
        form.groups.data = selectedGroups

        return render_template('editPattern.html', form=form, form2=form2, therapistLiteral=therapistLiteral)


@app.route('/verPautas', methods=['GET', 'POST'])
@login_required
def viewPatterns():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    if form.validate_on_submit():
        form.submitDone.data = 1

        queryResult = searchPatterns(form, int(form.pageNumber.data))
        form2 = PaginationForm(queryResult["numberPages"])
        form2.pagination.data = form.pageNumber.data

        return render_template('viewPatterns.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
            therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
            numberPages=queryResult["numberPages"])
        
    form.submitDone.data = 0
    return render_template('viewPatterns.html', form=form, form2=form2, therapistLiteral=therapistLiteral)


@app.route('/verGrupos', methods=['GET', 'POST'])
@login_required
def viewGroups():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = SearchGroupsForm()
    form2 = PaginationForm(1)

    if form.validate_on_submit():
        form.submitDone.data = 1

        queryResult = searchGroups(form, int(form.pageNumber.data))

        return render_template('viewGroups.html', form=form, form2=form2, rowGroups=queryResult["rows"], \
            therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
            numberPages=queryResult["numberPages"])

    form.submitDone.data = 0
    return render_template('viewGroups.html', form=form, form2=form2, therapistLiteral = therapistLiteral)


@app.route('/verPacientes', methods=['GET', 'POST'])
@login_required
def viewPatients():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatientsForm(current_user.get_id())
    form2 = PaginationForm(1)

    if form.validate_on_submit():
        form.submitDone.data = 1

        queryResult = searchPatients(form, int(form.pageNumber.data))
        form2 = PaginationForm(queryResult["numberPages"])
        form2.pagination.data = form.pageNumber.data

        return render_template('viewPatients.html', form=form, form2=form2, rowPatients=queryResult["rows"], \
            therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
            numberPages=queryResult["numberPages"])        

    form.submitDone.data = 0
    return render_template('viewPatients.html', form=form, form2=form2, therapistLiteral=therapistLiteral)


@app.route('/registrarPaciente', methods=['GET', 'POST'])
@login_required
def registerPatient():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = RegisterPatientForm()

    #syncNow is always checked
    form.syncNow.data = True

    if form.validate_on_submit():

        #{name, surname1, surname2, gender, age} must be univoque
        if mongoClient["patients"].count_documents({"therapist":current_user.get_id(), "name": form.name.data, \
            "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data, \
            "gender": form.gender.data}) == 0:
                
            registrationToken = generateUniqueRandom("tmpPatientToken", 'id')

            #Delete all possible temporal registers of tryouts to register this same user as they are no longer usefull
            mongoClient["tmpPatientToken"].delete_many({'name': form.name.data, 'surname1': form.surname1.data, \
                'surname2': form.surname2.data, 'surname2': form.surname2.data, "gender": form.gender.data})

            mongoClient["tmpPatientToken"].insert_one({'id': registrationToken, 'synced': False, \
                "name": form.name.data, "surname1": form.surname1.data, "surname2": form.surname2.data, \
                "age": form.age.data, "gender": form.gender.data, "timestamp" : int(time.time())})
            form.registrationToken.data = registrationToken

        
        else:
            form.syncHidden.data = "False"
            flash("Ya existe un paciente con estos credenciales", "error")
    
    else:
        form.syncHidden.data = "False"

        if form.name.data is None:
            form.name.data = ""
        
        if form.surname1.data is None:
            form.surname1.data = ""
        
        if form.surname2.data is None:
            form.surname2.data = ""
        
        if form.age.data is None:
            form.age.data = ""

    return render_template('registerPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral)


@app.route('/verPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def viewPatient(idPatient):
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe ese paciente", "error")
        return redirect(url_for('index'))

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = EditPatientForm(current_user.get_id())
    form2 = GenericEditForm()
    form3 = PaginationForm(1)
    form4 = PaginationForm2(1)

    if form.validate_on_submit():
        patternsSelected = list(map(int, form.patterns.data))
        groupsSelected = list(map(int, form.groups.data))
        newPatterns = patternsSelected
        
        cursorGroups = mongoClient["groups"].find({"id": {"$in": groupsSelected}})

        for cur in cursorGroups:
            newPatterns += cur["patterns"]


        mongoClient["patients"].update_one({"id":idPatient}, {"name": form.name.data, "surname1": form.surname1.data, \
            "surname2": form.surname2.data, "age": form.age.data, "gender": form.gender.data, "patterns": newPatterns})
        
        mongoClient["groups"].update_many({"id":{"$in": groupsSelected}}, {"$push": {"patients": idPatient}})

        flash("Paciente modificado correctamente", "success")
        return redirect(url_for('index'))
    
    else:
        form.patientId.data = idPatient


        cursor = mongoClient["patients"].find_one({"id":idPatient})
        cursor2 = mongoClient["groups"].find({"therapist": current_user.get_id(), "patients" : idPatient})

        selectedGroups = []

        for cur in cursor2:
            if "id" in cur:
                selectedGroups.append(str(cur["id"]))


        form.name.data = cursor["name"]
        form.surname1.data = cursor["surname1"]
        form.surname2.data = cursor["surname2"]
        form.age.data = cursor["age"]
        form.gender.data = cursor["gender"]
        form.patterns.data = list(map(str, cursor["patterns"]))
        form.groups.data = selectedGroups



    cursorPatient = mongoClient["patients"].find_one({"therapist":current_user.get_id(), "id": idPatient})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())



    
    queryResultPatterns = searchPatternsPatient(idPatient, 1)
    queryResultGroups = searchGroupsPatient(idPatient, 1)
    

    return render_template('viewPatient.html', therapistLiteral=therapistLiteral, patientInfo=patientInfo, \
        rowsPatterns=queryResultPatterns["rows"], rowsGroups=queryResultGroups["rows"], form=form, form2=form2, \
        form3=form3, form4=form4, idPatient=idPatient, pagesPatterns=queryResultPatterns["numberPages"], \
        pagesGroups=queryResultGroups["numberPages"], numberRowsPattern=queryResultPatterns["numberTotalRows"], \
        numberRowsGroup=queryResultGroups["numberTotalRows"])


@app.route('/registrarGrupo', methods=['GET', 'POST'])
@login_required
def registerGroup():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = RegistrationGroupForm(current_user.get_id())

    if form.validate_on_submit():

        if mongoClient["groups"].count_documents({"therapist": current_user.get_id(), "name":form.name.data}) == 0:
            #TODO: move this to a Mongo method

            idGroup = 1

            cursor = mongoClient["groups"].find({}).sort("id",-1).limit(1)
            #idGroup is incremental and univoque
            for cur in cursor:
                idGroup = cur["id"] + 1

            mongoClient["groups"].insert_one({'name': form.name.data, 'description': form.description.data, \
                'patients': list(map(int, form.patients.data)), 'patterns': list(map(int, form.patterns.data))})

            #Associate patients with patterns
            if len(form.patients.data) > 0 and len(form.patterns.data) > 0:
                for patient in list(map(int, form.patients.data)):
                    for pattern in list(map(int, form.patterns.data)):
                        mongoClient["patients"].update({"id":patient}, {"$push": {"patterns":pattern}})
            
            flash("Grupo creado correctamente", "info")
            return render_template('index.html')
        else:
            flash("Ya existe un grupo con ese nombre", "error")

    return render_template('registerGroup.html', form=form, therapistLiteral=therapistLiteral)


@app.route('/verPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def viewPattern(idPattern):

    if mongoClient["patterns"].count_documents({"therapist":current_user.get_id(), "id":idPattern}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(url_for('index'))

    cursorPattern = mongoClient["patterns"].find_one({"therapist":current_user.get_id(), "id": idPattern})

    intensity1 = "Sí" if 1 in cursorPattern["intensities"] else "no"
    intensity2 = "Sí" if 2 in cursorPattern["intensities"] else "no"
    intensity3 = "Sí" if 3 in cursorPattern["intensities"] else "no"

    patternInfo  = {"id": idPattern, "name":cursorPattern["name"], "description":cursorPattern["description"], 
        "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3}

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = PaginationForm(1)
    form2 = PaginationForm2(1)

    queryResultGroups = searchGroupsPattern(idPattern, 1)
    queryResultPatients = searchPatientsPattern(idPattern, 1)

    return render_template('viewPattern.html', therapistLiteral=therapistLiteral, patternInfo=patternInfo, \
        rowsGroups=queryResultGroups["rows"], rowsPatients=queryResultPatients["rows"], form=form, form2=form2, \
        idPattern=idPattern, pagesGroups=queryResultGroups["numberPages"], \
        pagesPatients=queryResultPatients["numberPages"], numberRowsPatient=queryResultPatients["numberTotalRows"], \
        numberRowsGroup=queryResultGroups["numberTotalRows"])


@app.route('/editarGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def editGroup(idGroup):

    if mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "id":idGroup}) == 0:
        flash("No existe el grupo de pautas especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    therapist = current_user.get_id()

    form = RegistrationGroupForm(current_user.get_id())
    form2 = GenericEditForm()

    if form.validate_on_submit():
        if mongoClient["groups"].count_documents({"therapist": current_user.get_id(), "name":form.name.data, \
            "id":{"$ne": idGroup}}) == 0:
            updateGroup(form, current_user.get_id(), idGroup)

            flash("Grupo modificado correctamente", "info")
            return render_template('index.html')
        else:
            flash("Ya existe un grupo con este nombre", "error")

    cursorGroup = mongoClient["groups"].find_one({"id":idGroup})

    form.name.data = cursorGroup["name"]
    form.description.data = cursorGroup["description"]
    form.patients.data = list(map (str, cursorGroup["patients"]))
    form.patterns.data = list(map (str, cursorGroup["patterns"]))

    return render_template('editGroup.html', therapistLiteral=therapistLiteral, idGroup=idGroup, \
        form=form, form2=form2)


@app.route('/verGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def viewGroup(idGroup):

    if mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "id":idGroup}) == 0:
        flash("No existe el grupo de pautas especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    therapist = current_user.get_id()

    form = PaginationForm(1)
    form2 = PaginationForm2(1)

    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id": idGroup})

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"], "description":cursorGroup["description"]}

    queryResultPatients = searchPatientsGroup(idGroup, 1)
    queryResultPatterns = searchPatternsGroup(idGroup, 1)


    return render_template('viewGroup.html', therapistLiteral=therapistLiteral, groupInfo=groupInfo,
        form=form, form2=form2, idGroup=idGroup, rowsPatients=queryResultPatients["rows"], \
        pagesPatients=queryResultPatients["numberPages"], numberRowsPatient=queryResultPatients["numberTotalRows"], \
        rowsPatterns=queryResultPatterns["rows"], pagesPatterns=queryResultPatterns["numberPages"], \
        numberRowsPattern=queryResultPatterns["numberTotalRows"])


    return render_template('viewGroup.html', rowPatterns=rowPatterns, therapistLiteral=therapistLiteral)


@app.route('/verEpisodios', methods=['GET', 'POST'])
@app.route('/verEpisodios/', methods=['GET', 'POST'])
@login_required
def viewEpisodesGeneric():

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = FilterByDateForm(current_user.get_id(), 1)
    form.submitDone.data = 0
    numberPages = 0
    patientInfo  = {}

    if form.validate_on_submit():

        form.submitDone.data = 1
        idPatient = int(form.patients.data)
        patientInfo  = {"id": idPatient}

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

        return render_template('viewEpisodesGeneric.html', form=form, therapistLiteral=therapistLiteral, \
            patientInfo=patientInfo, rowEpisodes=rowEpisodes, numberTotalRows=numberTotalRows, numberPages=numberPages)

    return render_template('viewEpisodesGeneric.html', form=form, therapistLiteral=therapistLiteral, \
        patientInfo=patientInfo)


@app.route('/verEpisodios/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def viewEpisodes(idPatient):

    if idPatient is not 0 and mongoClient["patients"].count_documents({"id":idPatient, \
        "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

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

        return render_template('viewEpisodes.html', form=form, therapistLiteral=therapistLiteral, \
            patientInfo=patientInfo, rowEpisodes=rowEpisodes, numberTotalRows=numberTotalRows, numberPages=numberPages)

    return render_template('viewEpisodes.html', form=form, therapistLiteral=therapistLiteral, patientInfo=patientInfo)

@app.route('/verUnEpisodio', methods=['GET', 'POST'])
@login_required
def viewOneEpisode():
    if request.args.get('idPatient') is None or request.args.get('timestampFrom') is None or \
        request.args.get('timestampTo') is None:
        flash("Es necesario especificar el paciente y el intervalo temporal", "error")

    idPatient = int(request.args.get('idPatient'))

    if mongoClient["patients"].count_documents({"id":idPatient, "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    timestampFrom = int(request.args.get('timestampFrom'))
    timestampTo = int(request.args.get('timestampTo'))

    rowEpisodes = getOneEpisode(timestampFrom, timestampTo, idPatient)

    return render_template('viewOneEpisode.html', rowEpisodes=rowEpisodes, therapistLiteral=therapistLiteral)

########################################################################################################################

#TODO

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    return render_template('index.html', therapistLiteral=therapistLiteral)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))



