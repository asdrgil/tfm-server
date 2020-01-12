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
    searchPatientsGroup, searchPatternsGroup
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

        return render_template('editPattern.html', form=form, therapistLiteral=therapistLiteral)


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
    else:
        form.submitDone.data = 0
        return render_template('viewPatterns.html', form=form, form2=form2, therapistLiteral=therapistLiteral)



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

        if form.windowToken.data == None:
            form.windowToken.data = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

    return render_template('registerPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral)


@app.route('/verPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def editPatient(idPatient):
    idPatient = int(idPatient)
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe ese paciente", "error")
        return redirect(url_for('index'))

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = EditPatientForm()
    form2 = RegisterPatternForm2()

    if form.validate_on_submit():
        
        #Update PATTERNS from the patient
        if form.pattIds.data != None and len(form.pattIds.data) > 0:
            pattIds = [int(elem) for elem in form.pattIds.data.split(",")]
            windowToken = form.windowToken.data
            queryPattIds = []

            #Persist all patterns
            for pattern in pattIds:
                queryPattIds.append({'id': pattern, "windowId":windowToken})
            
            if mongoClient["patterns"].count_documents({"$or": queryPattIds}) > 0:
                cursor = mongoClient["patterns"].find({"$or": queryPattIds})

                #Persist new created patterns
                for cur in cursor:
                    mongoClient["patterns"].update_one({"id":cur["id"]}, {"$unset": {"windowId":1}})

            #Bond all patterns from select or new created patterns to the current user
            mongoClient["patients"].update_one({"id":idPatient}, {"$set": {"patterns": pattIds}})

        else:
            mongoClient["patients"].update_one({"id":cur["id"]}, {"$unset": {"patterns":1}})

        #Update GROUPS from the patient
        if form.groups.data != None and len(form.groups.data) > 0:
            for group in form.groups.data:
                mongoClient["groups"].update({"id":int(group)}, {"$push": {"patients":idPatient}})

        #Remove temporal registers as they are no longer neccesary
        mongoClient["tmpPatterns"].delete_many({"windowId":windowToken})

        #Redirect index and flash all OK
        flash("Paciente modificado correctamente", "success")
        return redirect(url_for('index'))
    else:
        if form.patientId.data == None:
            form.patientId.data = idPatient

        if form.windowToken.data == None:
            form.windowToken.data = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

        if cursorPatient["synced"] == True:
            form.synced.data = "True"
        else:
            form.synced.data = "False"

        cursor = mongoClient["patients"].find_one({"id":idPatient})
        cursor2 = mongoClient["groups"].find({"patients" : idPatient})

        if form.pattIds.data == None:
            form.pattIds.data = ','.join(str(x) for x in cursor["patterns"])

        selectedGroups = []
        for cur in cursor2:
            if "id" in cur:
                selectedGroups.append(str(cur["id"]))


        form.name.data = cursor["name"]
        form.surname1.data = cursor["surname1"]
        form.surname2.data = cursor["surname2"]
        form.age.data = cursor["age"]
        form.patterns.data = list(map(str, cursor["patterns"]))
        form.groups.data = selectedGroups

        #Fill table of patterns
        rowPatterns = []

        cursor3 = mongoClient["patterns"].find({"therapist": current_user.get_id(), "id": {"$in" : cursor["patterns"]}})

        for cur in cursor3:
            description = ""
            intensity1 = "No"
            intensity2 = "No"
            intensity3 = "No"
            if "description" in cur:
                description = cur["description"]

            if "intensities" in cur:
                if 1 in cur["intensities"]:
                    intensity1 = "Sí"
                if 2 in cur["intensities"]:
                    intensity2 = "Sí"
                if 3 in cur["intensities"]:
                    intensity3 = "Sí"

            rowPatterns.append({"id": cur["id"], "name": cur["name"], "description": description, \
                "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3})
            mongoClient["tmpPatterns"].insert_one({"windowId": form.windowToken.data, "id": cur["id"], \
                "name": cur["name"], "decription": description, \
                "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3, "pattType":"selectPatt"})

        return render_template('editPatient.html', form=form, form2=form2, rowPatterns=rowPatterns, \
            therapistLiteral=therapistLiteral)


@app.route('/registrarGrupo', methods=['GET', 'POST'])
@login_required
def registerGroup():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = RegistrationGroupForm(current_user.get_id())

    if form.validate_on_submit():

        if mongoClient["groups"].count_documents({"name":form.name.data}) == 0:
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
            flash("Ya existe un grupo con ese nombre", "warning")

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

    return render_template('viewPattern.html', therapistLiteral=therapistLiteral, patternInfo=patternInfo,
        rowsGroups=queryResultGroups["rows"], rowsPatients=queryResultPatients["rows"], form=form, form2=form2, \
        idPattern=idPattern, pagesGroups=queryResultGroups["numberPages"], \
        pagesPatients=queryResultPatients["numberPages"], numberRowsPatient=queryResultPatients["numberTotalRows"], \
        numberRowsGroup=queryResultGroups["numberTotalRows"])


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


@app.route('/verPacientes', methods=['GET', 'POST'])
@login_required
def viewPatients():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatientsForm()

    if form.validate_on_submit():
        rowPatients = searchPatients(form)
        return render_template('viewPatients.html', form=form, rowPatients=rowPatients, \
            therapistLiteral=therapistLiteral)

    return render_template('viewPatients.html', form=form, therapistLiteral=therapistLiteral)

@app.route('/verGrupos', methods=['GET', 'POST'])
@login_required
def viewGroups():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = SearchGroupsForm()

    if form.validate_on_submit():
        rowGroups = searchGroups(form)
        return render_template('viewGroups.html', form=form, rowGroups=rowGroups, therapistLiteral = therapistLiteral)

    return render_template('viewGroups.html', form=form, therapistLiteral = therapistLiteral)


@app.route('/verEpisodios', methods=['GET', 'POST'])
@login_required
def viewEpisodes():
    
    idPatient = 0 if request.args.get('idPatient') is None else request.args.get('idPatient')

    if idPatient is not 0 and mongoClient["patients"].count_documents({"id":idPatient, \
        "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = FilterByDateForm()

    form.patients.data = idPatient


    if form.validate_on_submit():

        idPatient = int(form.patientId.data)

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

        rowEpisodes = getMultipleEpisodes(timestampFrom, timestampTo, idPatient)
        return render_template('viewEpisodes.html', form=form,therapistLiteral=therapistLiteral,rowEpisodes=rowEpisodes)

    return render_template('viewEpisodes.html', form=form, therapistLiteral=therapistLiteral)

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

    form = TryoutForm()



    return render_template('viewOneEpisode.html', rowEpisodes=rowEpisodes, therapistLiteral=therapistLiteral, form=form)

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
