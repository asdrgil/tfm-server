from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.forms import LoginForm, RegisterTherapistForm, RegisterPatientForm, RegisterPatternForm, \
    RegistrationGroupForm, EditPatternForm, SearchPatternsForm, SearchPatientsForm, SearchGroupsForm, EditPatientForm, \
    GenericEditForm, FilterByDateForm, PaginationForm, PaginationForm2
from app.models import User
import math
from datetime import datetime
import time
from .mongoMethods import searchPatterns, searchPatients, searchGroups, getMultipleEpisodes, getOneEpisode, \
    generateUniqueRandom, updatePattern, searchGroupsPattern, searchPatientsPattern, \
    searchPatternsGroup, updateGroup, searchPatternsPatient, getCountMultipleEpisodes
from .constants import mongoClient, rowsPerPage
from .routesApi import syncDevice


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

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

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
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)


@app.route('/registrarPautaPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def registerPatternPatient(idPatient):
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe el paciente especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

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
            return redirect(url_for('viewPatient', idPatient=idPatient))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")

    form = RegisterPatternForm(current_user.get_id())

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    return render_template('registerPatternPatient.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral, patientInfo=patientInfo, rowsBreadCrumb=rowsBreadCrumb)


@app.route('/registrarPautaGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def registerPatternGroup(idGroup):
    if mongoClient["groups"].count_documents({"id":idGroup, "therapist":current_user.get_id()}) == 0:
        flash("No existe el grupo especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = RegisterPatternForm(current_user.get_id())

    cursorGroup = mongoClient["groups"].find_one({"id": idGroup})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verGrupos", "name":"Ver grupos"}, \
        {"href": "/verGrupo/" + str(idGroup) , "name": cursorGroup["name"]}]

    if form.validate_on_submit():

        form.name.data = form.name.data.strip()

        #The patternName must be univoque
        if mongoClient["patterns"].count_documents({"therapist": current_user.get_id(), "name":form.name.data}) == 0:

            cursor = mongoClient["patterns"].find({}).sort("id",-1).limit(1)
            
            #idPattern is incremental and univoque
            idPattern = 1
            for cur in cursor:
                idPattern = cur["id"] + 1

            mongoClient["groups"].update_one({"id" : idGroup}, {"$push": {"patterns":idPattern}})

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
            return redirect(url_for('viewGroup', idGroup=idGroup))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")

    form = RegisterPatternForm(current_user.get_id())

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"], "description":cursorGroup["description"]}

    return render_template('registerPatternGroup.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral, groupInfo=groupInfo, rowsBreadCrumb=rowsBreadCrumb)


@app.route('/editarPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def editPattern(idPattern):
    if mongoClient["patterns"].count_documents({"id":idPattern, "therapist":current_user.get_id()}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    cursorPattern = mongoClient["patterns"].find_one({"id":idPattern})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}, \
        {"href": "/verPauta/" + str(idPattern), "name": cursorPattern["name"]}]
    
    form = EditPatternForm(current_user.get_id())
    form2 = GenericEditForm()

    if form.validate_on_submit():
        updatePattern(form, current_user.get_id())
        
        flash("Pauta modificada correctamente", "success")
        return redirect(url_for('index'))

    else:

        form.patternId.data = idPattern

        patternData = mongoClient["patterns"].find_one({"id":int(idPattern), "therapist":current_user.get_id()})

        form.name.data = patternData["name"]
        form.description.data = patternData["description"]

        if "intensities" in patternData:
            form.intensity1.data = 1 in patternData["intensities"]
            form.intensity2.data = 2 in patternData["intensities"]
            form.intensity3.data = 3 in patternData["intensities"]

        return render_template('editPattern.html', form=form, form2=form2, therapistLiteral=therapistLiteral, \
            rowsBreadCrumb=rowsBreadCrumb)


@app.route('/verPautas', methods=['GET', 'POST'])
@login_required
def viewPatterns():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    if request.args.get('deleteElem') is not None:
        mongoClient["patterns"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Pauta eliminada correctamente", "info")

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.patients.data = ""
        form.intensities.data = ""
        form.groups.data = ""
        form.pageNumber.data = "1"


    queryResult = searchPatterns(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('viewPatterns.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb)


@app.route('/enlazarPautasPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def linkPatternsPatient(idPatient):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    cursorPatient = mongoClient["patients"].find_one({"therapist":current_user.get_id(), "id": idPatient})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient), "name": cursorPatient["name"] + " " + cursorPatient["surname1"]}]


    if form.validate_on_submit() is False:
        form.name.data = ""
        form.patients.data = []
        form.groups.data = []
        form.intensities.data = []
        form.pageNumber.data = "1"

    queryResult = searchPatterns(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('linkPatternsPatient.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], patientInfo=patientInfo, rowsBreadCrumb=rowsBreadCrumb)
        

@app.route('/enlazarPautasGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def linkPatternsGroup(idGroup):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id": idGroup})

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verGrupos", "name":"Ver grupos"}, \
        {"href": "/verGrupo/" + str(idGroup), "name": cursorGroup["name"]}]


    if form.validate_on_submit() is False:
        form.name.data = ""
        form.patients.data = []
        form.groups.data = []
        form.intensities.data = []
        form.pageNumber.data = "1"

    queryResult = searchPatterns(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('linkPatternsGroup.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], groupInfo=groupInfo, rowsBreadCrumb=rowsBreadCrumb)


@app.route('/verGrupos', methods=['GET', 'POST'])
@login_required
def viewGroups():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = SearchGroupsForm()
    form2 = PaginationForm(1)

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    if request.args.get('deleteElem') is not None:
        mongoClient["groups"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Grupo de pautas eliminado correctamente", "info")    

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.patterns.data = ""
        form.pageNumber.data = "1"


    queryResult = searchGroups(form, int(form.pageNumber.data))

    return render_template('viewGroups.html', form=form, form2=form2, rowGroups=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb)


@app.route('/enlazarGruposPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def linkGroupsPattern(idPattern):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = SearchGroupsForm()
    form2 = PaginationForm(1)

    cursorPattern = mongoClient["patterns"].find_one({"id":idPattern})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}, \
        {"href": "/verPauta/" + str(idPattern), "name": cursorPattern["name"]}]

    cursorPattern = mongoClient["patterns"].find_one({"therapist":current_user.get_id(), "id": idPattern})

    intensity1 = "Sí" if 1 in cursorPattern["intensities"] else "No"
    intensity2 = "Sí" if 2 in cursorPattern["intensities"] else "No"
    intensity3 = "Sí" if 3 in cursorPattern["intensities"] else "No"

    patternInfo  = {"id": idPattern, "name":cursorPattern["name"], "description":cursorPattern["description"], 
        "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3}        

    if request.args.get('deleteElem') is not None:
        mongoClient["groups"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Grupo de pautas eliminado correctamente", "info")    

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.patients.data = ""
        form.patterns.data = ""
        form.pageNumber.data = "1"

    queryResult = searchGroups(form, int(form.pageNumber.data))

    return render_template('linkGroupsPattern.html', form=form, form2=form2, rowGroups=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb, patternInfo=patternInfo)


@app.route('/verPacientes', methods=['GET', 'POST'])
@login_required
def viewPatients():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
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

    return render_template('viewPatients.html', form=form, form2=form2, rowPatients=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb)


#TODO
@app.route('/enlazarPacientesPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def linkPatientsPattern(idPattern):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
    form = SearchPatientsForm(current_user.get_id())
    form2 = PaginationForm(1)

    cursorPattern = mongoClient["patterns"].find_one({"therapist":current_user.get_id(), "id": idPattern})

    intensity1 = "Sí" if 1 in cursorPattern["intensities"] else "No"
    intensity2 = "Sí" if 2 in cursorPattern["intensities"] else "No"
    intensity3 = "Sí" if 3 in cursorPattern["intensities"] else "No"

    patternInfo  = {"id": idPattern, "name":cursorPattern["name"], "description":cursorPattern["description"], 
        "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}, \
        {"href": "/verPauta/" + str(idPattern), "name": cursorPattern["name"]}]

    if request.args.get('linkPatt') is not None:
        mongoClient["patients"].update_one({"id": int(request.args.get('linkPatt'))}, {"$push": \
            {"patterns": idPattern}})
        flash("Pauta vinculada correctamente al paciente", "info")

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.surname1.data = ""
        form.surname2.data = ""
        form.age.data = ""
        form.genders.data = ""
        form.patterns.data = ""
        form.pageNumber.data = "1"


    queryResult = searchPatients(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('linkPatientsPattern.html', form=form, form2=form2, rowPatients=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb, patternInfo=patternInfo)


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

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    return render_template('registerPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)


@app.route('/modificarPaciente/<int:idPatient>', methods=['GET', 'POST'])
@login_required
def modifyPatient(idPatient):
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())
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
            return redirect(url_for('viewPatient', idPatient=idPatient))
        
        else:
            flash("Ya existe un paciente con estos credenciales", "error")
    
    else:

        form.name.data = cursorPatient["name"]
        form.surname1.data = cursorPatient["surname1"]
        form.surname2.data = cursorPatient["surname2"]
        form.age.data = int(cursorPatient["age"])
        form.gender.data = cursorPatient["gender"]

    return render_template('modifyPatient.html', title='RegisterPatient', form=form, \
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)

@app.route('/verPaciente/<int:idPatient>', methods=['GET', 'POST'])
@app.route('/verPaciente/<int:idPatient>/', methods=['GET', 'POST'])
@login_required
def viewPatient(idPatient):
    if mongoClient["patients"].count_documents({"id":idPatient, "therapist":current_user.get_id()}) == 0:
        flash("No existe ese paciente", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist":current_user.get_id()})

    patientInfo  = {"id": idPatient, "name":cursorPatient["name"], "surname1":cursorPatient["surname1"], \
        "surname2":cursorPatient["surname2"], "age":cursorPatient["age"], "gender":cursorPatient["gender"]}

    form = EditPatientForm(current_user.get_id())
    form2 = GenericEditForm()
    form3 = PaginationForm(1)
    form4 = FilterByDateForm(current_user.get_id(), 1)

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}]

    #Unlink pattern
    if request.args.get("unlinkPatt") is not None:
        mongoClient["patients"].update_one({"id":idPatient}, {"$pull": \
            {"patterns": int(request.args.get("unlinkPatt"))}})


    if form.validate_on_submit():

        #{name, surname1, surname2, gender, age} must be univoque
        if mongoClient["patients"].count_documents({"therapist":current_user.get_id(), "name": form.name.data, \
            "surname1": form.surname1.data, "surname2": form.surname2.data, "age": form.age.data, \
            "gender": form.gender.data}) == 0:

            mongoClient["patients"].update_one({"id":idPatient}, {"name": form.name.data, "surname1": form.surname1.data, \
            "surname2": form.surname2.data, "age": form.age.data, "gender": form.gender.data})
            flash("Paciente modificado correctamente", "success")
            return redirect(url_for('index'))
        
        else:
            form.syncHidden.data = "False"
            flash("Ya existe un paciente con estos credenciales", "error")

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient})
        
    form.name.data = cursorPatient["name"]
    form.surname1.data = cursorPatient["surname1"]
    form.surname2.data = cursorPatient["surname2"]
    form.age.data = cursorPatient["age"]
    form.gender.data = cursorPatient["gender"]

    queryResultPatterns = searchPatternsPatient(idPatient, 1, "arr")

    return render_template('viewPatient.html', therapistLiteral=therapistLiteral, \
        rowsPatterns=queryResultPatterns["rows"], form=form, form2=form2, \
        form3=form3, form4=form4, idPatient=idPatient, pagesPatterns=queryResultPatterns["numberPages"], \
        numberRowsPattern=queryResultPatterns["numberTotalRows"], rowsBreadCrumb=rowsBreadCrumb, \
        patientInfo=patientInfo)


@app.route('/registrarGrupo', methods=['GET', 'POST'])
@login_required
def registerGroup():
    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = RegistrationGroupForm(current_user.get_id())

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    if form.validate_on_submit():

        if mongoClient["groups"].count_documents({"therapist": current_user.get_id(), "name":form.name.data}) == 0:
            #TODO: move this to a Mongo method

            idGroup = 1

            cursor = mongoClient["groups"].find({}).sort("id",-1).limit(1)
            #idGroup is incremental and univoque
            for cur in cursor:
                idGroup = cur["id"] + 1

            mongoClient["groups"].insert_one({'name': form.name.data, 'description': form.description.data, \
                'patterns': list(map(int, form.patterns.data)), "id":idGroup})
            
            flash("Grupo creado correctamente", "info")
            return render_template('index.html')
        else:
            flash("Ya existe un grupo con ese nombre", "error")

    return render_template('registerGroup.html', form=form, therapistLiteral=therapistLiteral, \
        rowsBreadCrumb=rowsBreadCrumb)


@app.route('/verPauta/<int:idPattern>', methods=['GET', 'POST'])
@login_required
def viewPattern(idPattern):

    if mongoClient["patterns"].count_documents({"therapist":current_user.get_id(), "id":idPattern}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(url_for('index'))

    #Unlink pattern
    if request.args.get("unlinkPati") is not None:
        mongoClient["patients"].update_one({"id":int(request.args.get("unlinkPati"))}, {"$pull": \
            {"patterns": idPattern}})

    #Unlink group
    if request.args.get("unlinkGroup") is not None:
        mongoClient["groups"].update_one({"id":int(request.args.get("unlinkGroup"))}, {"$pull": \
            {"patterns": idPattern}})    

    cursorPattern = mongoClient["patterns"].find_one({"therapist":current_user.get_id(), "id": idPattern})

    intensity1 = "Sí" if 1 in cursorPattern["intensities"] else "No"
    intensity2 = "Sí" if 2 in cursorPattern["intensities"] else "No"
    intensity3 = "Sí" if 3 in cursorPattern["intensities"] else "No"

    patternInfo  = {"id": idPattern, "name":cursorPattern["name"], "description":cursorPattern["description"], 
        "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3}

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}]

    form = PaginationForm(1)
    form2 = PaginationForm2(1)

    queryResultGroups = searchGroupsPattern(idPattern, 1)
    queryResultPatients = searchPatientsPattern(idPattern, 1)

    return render_template('viewPattern.html', therapistLiteral=therapistLiteral, patternInfo=patternInfo, \
        rowsGroups=queryResultGroups["rows"], rowsPatients=queryResultPatients["rows"], form=form, form2=form2, \
        idPattern=idPattern, pagesGroups=queryResultGroups["numberPages"], \
        pagesPatients=queryResultPatients["numberPages"], numberRowsPatient=queryResultPatients["numberTotalRows"], \
        numberRowsGroup=queryResultGroups["numberTotalRows"], rowsBreadCrumb=rowsBreadCrumb)


@app.route('/editarGrupo/<int:idGroup>', methods=['GET', 'POST'])
@login_required
def editGroup(idGroup):

    if mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "id":idGroup}) == 0:
        flash("No existe el grupo de pautas especificado", "error")
        return redirect(url_for('index'))

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

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

    form = PaginationForm(1)
    form2 = PaginationForm2(1)

    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id": idGroup})

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"], "description":cursorGroup["description"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}]

    queryResultPatterns = searchPatternsGroup(idGroup, 1)


    return render_template('viewGroup.html', therapistLiteral=therapistLiteral, groupInfo=groupInfo,
        form=form, form2=form2, idGroup=idGroup, rowsPatterns=queryResultPatterns["rows"], \
        pagesPatterns=queryResultPatterns["numberPages"], numberRowsPattern=queryResultPatterns["numberTotalRows"], \
        rowsBreadCrumb=rowsBreadCrumb)


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():

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

        elif len(form.time1.data) == 0:
            form.time1.data = "00:00"

        #TO
        if len(form.date2.data) == 0:
            form.date2.data = "2050-01-01"
            form.time2.data = "23:59"

        elif len(form.time2.data) == 0:
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


@app.route('/index2', methods=['GET', 'POST'])
@login_required
def index2():

    therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
        current_user.get_surname2())

    form = SearchPatientsForm(current_user.get_id())

    rowPatients = []
    cursorPatients = mongoClient["patients"].find({"therapist":current_user.get_id()})
    numberTotalRows = mongoClient["patients"].count_documents({"therapist":current_user.get_id()})

    for cur in cursorPatients:
        rowPatients.append({"id": cur["id"], "name": cur["name"] , "surname1": cur["surname1"], \
            "surname2": cur["surname2"], "age": cur["age"], "gender": cur["gender"]})


    return render_template('index2.html', therapistLiteral=therapistLiteral, \
        rowPatients=rowPatients, numberTotalRows=numberTotalRows, form=form)


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

    cursorPatient = mongoClient["patients"].find_one({"id":idPatient, "therapist": current_user.get_id()})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}, \
        {"href": "/verPaciente/" + str(idPatient), "name": cursorPatient["name"] + " " + cursorPatient["surname1"]}]    

    timestampFrom = int(request.args.get('timestampFrom'))
    timestampTo = int(request.args.get('timestampTo'))

    rowEpisodes = getOneEpisode(timestampFrom, timestampTo, idPatient)

    return render_template('viewOneEpisode.html', rowEpisodes=rowEpisodes, therapistLiteral=therapistLiteral, \
        rowsBreadCrumb=rowsBreadCrumb)

########################################################################################################################

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))



