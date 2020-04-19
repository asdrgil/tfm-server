from flask import render_template, flash, redirect, request, url_for, request
from flask_login import current_user, login_required
from app import db
from app.views.patterns import bp
from app.forms import RegisterPatternForm, SearchPatternsForm, PaginationForm, EditPatternForm, GenericEditForm, \
    SearchPatientsForm, PaginationForm2, SearchGroupsForm, PatientSelectForm, GroupSelectForm
from app.constants import mongoClient
from app.mongoMethods import searchPatterns, updatePattern, searchGroupsPattern, searchPatientsPattern, \
    searchPatients, searchGroups, registerTraceUsers
from app.constants import urlPrefix
from datetime import datetime

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
@bp.route('/registrarPauta', methods=['GET', 'POST'])
def registerPattern():
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
            return redirect(urlPrefix + url_for('general.index'))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")

    return render_template('patterns/registerPattern.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)


@login_required
@bp.route('/verPauta/<int:idPattern>', methods=['GET', 'POST'])
def viewPattern(idPattern):

    if mongoClient["patterns"].count_documents({"therapist":current_user.get_id(), "id":idPattern}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(urlPrefix + url_for('general.index'))

    cursorPattern = mongoClient["patterns"].find_one({"therapist":current_user.get_id(), "id": idPattern})

    intensity1 = "Sí" if 1 in cursorPattern["intensities"] else "No"
    intensity2 = "Sí" if 2 in cursorPattern["intensities"] else "No"
    intensity3 = "Sí" if 3 in cursorPattern["intensities"] else "No"

    patternInfo  = {"id": idPattern, "name":cursorPattern["name"], "description":cursorPattern["description"], 
        "intensity1":intensity1, "intensity2":intensity2, "intensity3":intensity3}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}]
    
    #UNLINK patient
    if request.args.get("unlinkPati") is not None:
        mongoClient["patients"].update_one({"id":int(request.args.get("unlinkPati"))}, {"$pull": \
            {"patterns": idPattern}})
        flash("Paciente desvinculado correctamente.", "success")

    #UNLINK group
    if request.args.get("unlinkGroup") is not None:
        mongoClient["groups"].update_one({"id":int(request.args.get("unlinkGroup"))}, {"$pull": \
            {"patterns": idPattern}})
        flash("Grupo desvinculado correctamente.", "success")            

    #LINK patients
    if request.args.get("linkPatis") is not None:
        patients = list(map(int, request.args.get("linkPatis").split(",")))
        mongoClient["patients"].update_many({"id": {"$in": list(map(int, patients))}}, \
            {"$push": {"patterns":idPattern}})
        flash("Pacientes vinculados correctamente.", "success")            
            
    #LINK groups
    if request.args.get("linkGroups") is not None:
        groups = list(map(int, request.args.get("linkGroups").split(",")))
        mongoClient["groups"].update_many({"id": {"$in": list(map(int, groups))}}, \
            {"$push": {"patterns":idPattern}})
        flash("Grupos vinculados correctamente.", "success")
        
    form = PaginationForm(1)
    form2 = PaginationForm2(1)
    form3 = PatientSelectForm([current_user.get_id(), idPattern])
    form4 = GroupSelectForm([current_user.get_id(), idPattern])

    queryResultGroups = searchGroupsPattern(idPattern, 1)
    queryResultPatients = searchPatientsPattern(idPattern, 1)

    return render_template('patterns/viewPattern.html', therapistLiteral=therapistLiteral, patternInfo=patternInfo, \
        rowsGroups=queryResultGroups["rows"], rowsPatients=queryResultPatients["rows"], form=form, form2=form2, \
        form3=form3, form4=form4, pagesGroups=queryResultGroups["numberPages"], \
        pagesPatients=queryResultPatients["numberPages"], numberRowsPatient=queryResultPatients["numberTotalRows"], \
        numberRowsGroup=queryResultGroups["numberTotalRows"], rowsBreadCrumb=rowsBreadCrumb)
        

@login_required
@bp.route('/editarPauta/<int:idPattern>', methods=['GET', 'POST'])
def editPattern(idPattern):
    if mongoClient["patterns"].count_documents({"id":idPattern, "therapist":int(current_user.get_id())}) == 0:
        flash("No existe la pauta especificada", "error")
        return redirect(urlPrefix + url_for('patterns.viewPatterns'))

    cursorPattern = mongoClient["patterns"].find_one({"id":idPattern})

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPautas", "name":"Ver pautas"}, \
        {"href": "/verPauta/" + str(idPattern), "name": cursorPattern["name"]}]
    
    form = EditPatternForm(current_user.get_id())
    form2 = GenericEditForm()

    if form.validate_on_submit():
        updatePattern(form, current_user.get_id())
        
        flash("Pauta modificada correctamente", "success")
        return redirect(urlPrefix + url_for('patterns.viewPattern', idPattern=idPattern))

    else:

        form.patternId.data = idPattern

        patternData = mongoClient["patterns"].find_one({"id":idPattern, "therapist":current_user.get_id()})

        form.name.data = patternData["name"]
        form.description.data = patternData["description"]

        if "intensities" in patternData:
            form.intensity1.data = 1 in patternData["intensities"]
            form.intensity2.data = 2 in patternData["intensities"]
            form.intensity3.data = 3 in patternData["intensities"]

        return render_template('patterns/editPattern.html', form=form, form2=form2, \
            therapistLiteral=therapistLiteral, rowsBreadCrumb=rowsBreadCrumb)


#TODO
@login_required
@bp.route('/enlazarPacientesPauta/<int:idPattern>', methods=['GET', 'POST'])
def linkPatientsPattern(idPattern):
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

    #Link pattern to patients
    if request.args.get("patiIds") is not None:
        patiIds = list(map(int, request.args.get("patiIds").split(",")))

        for pati in patiIds:
            mongoClient["patients"].update_one({"id":int(pati)}, { "$push": {"patterns": idPattern}})

        flash("Pautas vinculadas al paciente correctamente", "success")

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.surname1.data = ""
        form.surname2.data = ""
        form.age.data = ""
        form.genders.data = ""
        form.patterns.data = ""
        form.pageNumber.data = "1"


    queryResult = searchPatients(form, int(form.pageNumber.data), {"type":"patterns", "id":idPattern})
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('patterns/linkPatientsPattern.html', form=form, form2=form2, rowPatients=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb, patternInfo=patternInfo)
        

@login_required
@bp.route('/enlazarGruposPauta/<int:idPattern>', methods=['GET', 'POST'])
def linkGroupsPattern(idPattern):

    form = SearchGroupsForm(current_user.get_id())
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

    return render_template('patterns/linkGroupsPattern.html', form=form, form2=form2, rowGroups=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb, patternInfo=patternInfo)


@login_required
@bp.route('/verPautas', methods=['GET', 'POST'])
def viewPatterns():

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    #Delete element
    if request.args.get('deleteElem') != None:
        mongoClient["patterns"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Pauta eliminada correctamente", "info")

    #Set form values to zero on first load
    if form.validate_on_submit() != True:
        form.name.data = ""
        form.patients.data = ""
        form.intensities.data = ""
        form.groups.data = ""
        form.pageNumber.data = "1"


    queryResult = searchPatterns(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('patterns/viewPatterns.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb)
