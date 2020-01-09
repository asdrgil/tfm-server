from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db, socketio, thread_lock, thread
from app.forms import LoginForm, RegisterTherapistForm, RegisterPatientForm, RegisterPatternForm, RegistrationGroupForm, ViewPatternForm, SearchPatternsForm, SearchPatientsForm, SearchGroupsForm, EditPatientForm, RegisterPatternForm2, GenericEditForm, FilterByDateForm, TryoutForm
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
from operator import itemgetter
from .socketIOMethods import editPatternSocket, changedSelectGroup, changedSelectPattern, registerPatientEvent, insertNewPattern, insertPatient, getTmpPatterns
from .mongoMethods import searchPatterns, searchPatients, searchGroups, getMultipleEpisodes, getOneEpisode


#Constants
mongoClient = MongoClient('localhost:27017').tfm

def generateUniqueRandom(tokenType):
    token = ''.join(random.choice('0123456789ABCDEF') for i in range(6))

    while mongoClient[tokenType].find({"communicationId":token}).count() > 0:
        generateUniqueRandom(token)

    print("Token: {}".format(token))

    return token

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
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = RegisterPatternForm()

    if form.validate_on_submit():

        form.name.data = form.name.data.strip()

        #The patternName must be univoque
        if mongoClient["patterns"].count_documents({"name":form.name.data, "therapist": current_user.get_id()}) == 0:

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

            mongoClient["patterns"].insert_one({'name': form.name.data, 'description': form.description.data.strip(), 'intensities': intensities, "id":idPattern, "therapist":current_user.get_id()})
            
            flash("Pauta creada correctamente.", "success")
            return redirect(url_for('index'))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")



    return render_template('registerPattern.html', title='Registrar una pauta', form=form, therapistLiteral=therapistLiteral)


@app.route('/verPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def editPattern(idPattern):
    if mongoClient["patterns"].count_documents({"id":int(idPattern), "therapist":current_user.get_id()}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = ViewPatternForm()

    if form.validate_on_submit():

        intensities = []

        if form.intensity1.data:
            intensities.append(1)

        if form.intensity2.data:
            intensities.append(2)

        if form.intensity3.data:
            intensities.append(3)


        mongoClient["patterns"].update_one({"id" : idPattern}, {"$set" : {"name" : form.name.data, "description" : form.description.data, "intensities" : intensities, "patients" : list(map(int, form.patients.data)), "groups" : list(map(int, form.groups.data))}})
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
            form.intensity1.data = 1 in patternData["intensities"] or "1" in patternData["intensities"]
            form.intensity2.data = 2 in patternData["intensities"] or "2" in patternData["intensities"]
            form.intensity3.data = 3 in patternData["intensities"] or "3" in patternData["intensities"]

        selectedPatients = []

        for cur in cursorPatients:
            selectedPatients.append(str(cur["id"]))

        selectedGroups = []

        for cur in cursorGroups:
            selectedGroups.append(str(cur["id"]))

        form.patients.data = selectedPatients
        form.groups.data = selectedGroups

        return render_template('editPattern.html', form=form, therapistLiteral=therapistLiteral)
        return render_template('editPattern.html', form=form, therapistLiteral=therapistLiteral)


@app.route('/registrarPaciente', methods=['GET', 'POST'])
@login_required
def registerPatient():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = RegisterPatientForm()
    form2 = RegisterPatternForm2()

    #Submit | New entry
    if form.validate_on_submit():

        #{name, surname1, surname2, age} must be univoque
        if mongoClient["patients"].count_documents({"name": form.name.data, "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data}) == 0:

            #If the sync process will be done now
            if form.syncHidden.data == "True":
                #Sometimes it unchecks when doing the submit for unknown
                form.syncNow.data = True
                
                registrationToken = generateUniqueRandom("patients")

                mongoClient["tmpPatientToken"].delete_many({'name': form.name.data, 'surname1': form.surname1.data, 'surname2': form.surname2.data, 'surname2': form.surname2.data})

                mongoClient["tmpPatientToken"].insert_one({'id': registrationToken, 'synced': False, "name": form.name.data, "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data, "groups": list(map(int, form.groups.data))})
                form.registrationToken.data = registrationToken
            else:
                insertPatient(form.windowToken.data, form.name.data, form.surname1.data, form.surname2.data, form.age.data, form.groups.data, False)
                flash("Usuario registrado correctamente", "info")
                return redirect(url_for('index'))

        
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
    
    patterns = []

    if form.groups.data != None:
        patterns = getTmpPatterns(form.windowToken.data, "arr")

    return render_template('registerPatient.html', title='RegisterPatient', form=form, form2=form2, patterns=patterns, therapistLiteral=therapistLiteral)


@app.route('/verPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def editPatient(idPatient):
    idPatient = int(idPatient)
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe ese paciente", "error")
        return redirect(url_for('index'))

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
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

            rowPatterns.append({"id": cur["id"], "name": cur["name"], "description": description, "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3})
            mongoClient["tmpPatterns"].insert_one({"windowId": form.windowToken.data, "id": cur["id"], "name": cur["name"], "decription": description, "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3, "pattType":"selectPatt"})

        return render_template('editPatient.html', form=form, form2=form2, rowPatterns=rowPatterns, therapistLiteral=therapistLiteral)


@app.route('/registrarGrupo', methods=['GET', 'POST'])
@login_required
def registerGroup():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = RegistrationGroupForm()
    form2 = RegisterPatternForm2()

    if form.validate_on_submit():


        oldPatterns = form.oldPatterns.data.split(";")
        newPatterns = form.newPatterns.data.split(";")

        patternsIds = []

        #SELECT patterns
        if len(oldPatterns[0]) > 0:
            for patt in oldPatterns:
                patternsIds.extend(patt)

        #INSERT patterns
        if len(newPatterns[0]) > 0:
        
            idPattern = 1

            if mongoClient["patterns"].count_documents({}) > 0:
                cur = mongoClient["patterns"].find({}).sort("id",-1).limit(1)
                
                for c in cur:
                    idPattern = c["id"] + 1

            for patt in newPatterns:
                cols = patt.split(",")
                mongoClient["patterns"].insert_one({'name': cols[0], 'description': cols[1], "intensities": cols[2:], "id": idPattern})
                patternsIds.extend(str(idPattern))
                idPattern += 1

        if mongoClient["groups"].count_documents({"name":form.name.data}) == 0:
            mongoClient["groups"].insert_one({'name': form.name.data, 'description': form.description.data, 'patientsIds': list(map(int, form.patients.data)), 'patterns': patternsIds})
            flash("Grupo creado correctamente", "info")
            #return render_template('index.html')
        else:
            flash("Ya existe un grupo con ese nombre", "warning")

    else:
        if form.windowToken.data == None:
            form.windowToken.data = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

    return render_template('registerGroup.html', form=form, form2=form2, therapistLiteral=therapistLiteral)


@app.route('/verGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def editGroup(idGroup):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    therapist = current_user.get_id()
    idGroup = int(idGroup)
    form = RegistrationGroupForm()
    form2 = RegisterPatternForm2()
    form3 = GenericEditForm()

    if form.validate_on_submit():

        #The group's name must be univoque
        if mongoClient["groups"].count_documents({"id":{"$ne":idGroup, "name":form.name.data, "therapist":therapist}}) > 0:
            flash("Ya exise un grupo con este nombre", "error")

        else:

            groupCursor = mongoClient["groups"].find_one({"id":idGroup})

            #Patients and patterns that used to be linked to the given group
            oldSelectedPatients = groupCursor["patients"]
            oldSelectedPatterns = groupCursor["patterns"]

            newSelectedPatterns = []

            #New patterns
            cursor = mongoClient["tmpPatterns"].find({"windowId":form.windowToken.data})

            for cur in cursor:
                newSelectedPatterns.append(cur["id"])

            newSelectedPatients = list(map(int, form.patients.data))

            #Patterns that are no longer linked to the group
            discardedPatterns = list(set(oldSelectedPatterns) - set(newSelectedPatterns))
            #Patients that are no longer linked to the group
            discardedPatients = list(set(oldSelectedPatients) - set(newSelectedPatients))

            #1) UPDATE GROUPS with all the fields
            mongoClient["groups"].update_one({"id":int(idGroup)}, {"$set": {"name":form.name.data, "description":form.description.data, "patterns": newSelectedPatterns, "patients": newSelectedPatients}})

            #2) DELETE OLD PATTERNS from PATIENTS that are no longer linked to this group
            cursor = mongoClient["patients"].find({"id":{"$in": oldSelectedPatients}})

            for cur in cursor:
                currentPatientPatterns = []

                if "patterns" in cur:
                    currentPatientPatterns = cur["patterns"]
                    newPatientPatterns = list(set(currentPatientPatterns) - set(discardedPatterns))
                mongoClient["patients"].update_one({"id":cur["id"]}, {"$set": {"patterns":newPatientPatterns}})


            #3) UPDATE NEW PATTERNS to NEW PATIENTS
            cursor = mongoClient["patients"].find({"id":{"$in": newSelectedPatients}})

            for cur in cursor:
                currentPatientPatterns = []

                if "patterns" in cur:
                    currentPatientPatterns = cur["patterns"]
                    newPatientPatterns = list(set(currentPatientPatterns) | set(newSelectedPatterns))
                mongoClient["patients"].update_one({"id":cur["id"]}, {"$set": {"patterns":newPatientPatterns}})

            #5) Redirect to index
            flash("Grupo modificado correctamente", "info")
            return redirect(url_for('index'))
    else:
        if form.windowToken.data == None:
            form.windowToken.data = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))


        groupCursor = mongoClient["groups"].find_one({"id":int(idGroup), "therapist":therapist})

        description = "" if "description" not in groupCursor else groupCursor["description"]

        selectedPatients = list(map(str, groupCursor["patients"]))
        selectedPatterns = list(map(str, groupCursor["patterns"]))

        form.name.data = groupCursor["name"]
        form.description.data = description
        form.patients.data = selectedPatients
        form.patterns.data = selectedPatterns


        #Obtain all the info regarding the selected patterns in order to print them
        queryPatterns = []
        rowPatterns = []

        for elem in selectedPatterns:
            queryPatterns.append({'id': int(elem)})

        cursorPatterns = mongoClient["patterns"].find({"$or": queryPatterns})

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


            mongoClient["tmpPatterns"].insert_one({"windowId": form.windowToken.data, "id": cur["id"], "name": cur["name"], "decription": description, "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3, "pattType":"selectPatt"})
            rowPatterns.append({"id": cur["id"], "name": cur["name"], "description": description, "intensity1": intensity1, "intensity2": intensity2, "intensity3": intensity3})

        return render_template('editGroup.html', form=form, form2=form2, form3=form3, rowPatterns=rowPatterns, therapistLiteral=therapistLiteral)


@app.route('/verPautas', methods=['GET', 'POST'])
@login_required
def viewPatterns():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = SearchPatternsForm()

    if form.validate_on_submit():
        rowPatterns = searchPatterns(form)
        return render_template('viewPatterns.html', form=form, rowPatterns=rowPatterns, therapistLiteral=therapistLiteral)

    return render_template('viewPatterns.html', form=form, therapistLiteral=therapistLiteral)


@app.route('/verPacientes', methods=['GET', 'POST'])
@login_required
def viewPatients():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    form = SearchPatientsForm()

    if form.validate_on_submit():
        rowPatients = searchPatients(form)
        return render_template('viewPatients.html', form=form, rowPatients=rowPatients, therapistLiteral=therapistLiteral)

    return render_template('viewPatients.html', form=form, therapistLiteral=therapistLiteral)

@app.route('/verGrupos', methods=['GET', 'POST'])
@login_required
def viewGroups():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())

    form = SearchGroupsForm()

    if form.validate_on_submit():
        rowGroups = searchGroups(form)
        return render_template('viewGroups.html', form=form, rowGroups=rowGroups, therapistLiteral = therapistLiteral)

    return render_template('viewGroups.html', form=form, therapistLiteral = therapistLiteral)


@app.route('/verEpisodios', methods=['GET', 'POST'])
@login_required
def viewEpisodes():
    
    idPatient = 0 if request.args.get('idPatient') is None else request.args.get('idPatient')

    if idPatient is not 0 and mongoClient["patients"].count_documents({"id":idPatient, "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())

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

        timestampFrom = int(datetime.strptime('{} {}'.format(form.date1.data, form.time1.data), '%Y-%m-%d %H:%M').strftime("%s"))
        timestampTo = int(datetime.strptime('{} {}'.format(form.date2.data, form.time2.data), '%Y-%m-%d %H:%M').strftime("%s"))

        rowEpisodes = getMultipleEpisodes(timestampFrom, timestampTo, idPatient)
        return render_template('viewEpisodes.html', form=form, therapistLiteral=therapistLiteral, rowEpisodes=rowEpisodes)

    return render_template('viewEpisodes.html', form=form, therapistLiteral=therapistLiteral)

@app.route('/verUnEpisodio', methods=['GET', 'POST'])
@login_required
def viewOneEpisode():
    if request.args.get('idPatient') is None or request.args.get('timestampFrom') is None or request.args.get('timestampTo') is None:
        flash("Es necesario especificar el paciente y el intervalo temporal", "error")

    idPatient = int(request.args.get('idPatient'))

    if mongoClient["patients"].count_documents({"id":idPatient, "therapist": current_user.get_id()}) == 0:
        flash("No se ha encontrado el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())

    timestampFrom = int(request.args.get('timestampFrom'))
    timestampTo = int(request.args.get('timestampTo'))

    rowEpisodes = getOneEpisode(timestampFrom, timestampTo, idPatient)

    form = TryoutForm()



    return render_template('viewOneEpisode.html', rowEpisodes=rowEpisodes, therapistLiteral=therapistLiteral, form=form)

####################################################################################################################################################

#TODO

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), current_user.get_surname2())
    return render_template('index.html', therapistLiteral=therapistLiteral)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))