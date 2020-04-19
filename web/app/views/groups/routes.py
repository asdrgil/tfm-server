from flask import render_template, flash, redirect, request, url_for, request
from flask_login import current_user, login_required
from app import db
from app.views.groups import bp
from app.forms import RegistrationGroupForm, PaginationForm, PaginationForm2, SearchGroupsForm, \
    RegisterPatternForm, GenericEditForm, SearchPatternsForm
from app.constants import mongoClient, urlPrefix
from app.mongoMethods import searchPatterns, searchPatternsGroup, searchGroups, updateGroup, registerTraceUsers
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
@bp.route('/registrarGrupo', methods=['GET', 'POST'])
def registerGroup():

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

            mongoClient["groups"].insert_one({"therapist":current_user.get_id(), \
                'name': form.name.data, 'description': form.description.data, \
                'patterns': list(map(int, form.patterns.data)), "id":idGroup})
            
            flash("Grupo creado correctamente", "info")
            return redirect(urlPrefix + url_for('general.index'))
        else:
            flash("Ya existe un grupo con ese nombre", "error")

    return render_template('groups/registerGroup.html', form=form, therapistLiteral=therapistLiteral, \
        rowsBreadCrumb=rowsBreadCrumb)
        

@login_required
@bp.route('/editarGrupo/<int:idGroup>', methods=['GET', 'POST'])
def editGroup(idGroup):

    if mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "id":idGroup}) == 0:
        flash("No existe el grupo de pautas especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    form = RegistrationGroupForm(current_user.get_id())
    form2 = GenericEditForm()

    if form.validate_on_submit():
        if mongoClient["groups"].count_documents({"therapist": current_user.get_id(), "name":form.name.data, \
            "id":{"$ne": idGroup}}) == 0:
            updateGroup(form, current_user.get_id(), idGroup)

            flash("Grupo modificado correctamente", "info")
            return redirect(urlPrefix + url_for('general.index'))
        else:
            flash("Ya existe un grupo con este nombre", "error")

    cursorGroup = mongoClient["groups"].find_one({"id":idGroup})

    form.name.data = cursorGroup["name"]
    form.description.data = cursorGroup["description"]
    form.patterns.data = list(map (str, cursorGroup["patterns"]))

    return render_template('groups/editGroup.html', therapistLiteral=therapistLiteral, idGroup=idGroup, \
        form=form, form2=form2)

        
@login_required
@bp.route('/verGrupo/<int:idGroup>', methods=['GET', 'POST'])
def viewGroup(idGroup):

    if mongoClient["groups"].count_documents({"therapist":current_user.get_id(), "id":idGroup}) == 0:
        flash("No existe el grupo de pautas especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))

    #UNLINK pattern
    if request.args.get("unlinkPatt") is not None:
        mongoClient["groups"].update_one({"id":idGroup}, {"$pull": \
            {"patterns": int(request.args.get("unlinkPatt"))}})
        flash("Pauta desvinculada correctamente.", "success")

    #LINK patterns
    if request.args.get("linkPatts") is not None:
        patterns = list(map(int, request.args.get("linkPatts").split(",")))
        for patt in patterns:
            mongoClient["groups"].update_one({"id": idGroup}, \
                {"$push": {"patterns":patt}})
        flash("Pautas vinculadas correctamente.", "success")

    form = PaginationForm(1)
    form2 = PaginationForm2(1)

    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id": idGroup})

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"], "description":cursorGroup["description"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verPacientes", "name":"Ver pacientes"}]

    queryResultPatterns = searchPatternsGroup(idGroup, 1)

    return render_template('groups/viewGroup.html', therapistLiteral=therapistLiteral, groupInfo=groupInfo,
        form=form, form2=form2, idGroup=idGroup, rowsPatterns=queryResultPatterns["rows"], \
        pagesPatterns=queryResultPatterns["numberPages"], numberRowsPattern=queryResultPatterns["numberTotalRows"], \
        rowsBreadCrumb=rowsBreadCrumb)


@login_required
@bp.route('/verGrupos', methods=['GET', 'POST'])
def viewGroups():

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}]

    if request.args.get('deleteElem') is not None:
        mongoClient["groups"].delete_one({"id": int(request.args.get('deleteElem'))})
        flash("Grupo de pautas eliminado correctamente", "info")

    form = SearchGroupsForm(current_user.get_id())

    if form.validate_on_submit() is not True:
        form.name.data = ""
        form.patterns.data = ""
        form.pageNumber.data = "1"

    queryResult = searchGroups(form, int(form.pageNumber.data))
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data    

    return render_template('groups/viewGroups.html', form=form, form2=form2, rowGroups=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], rowsBreadCrumb=rowsBreadCrumb)
        

@login_required
@bp.route('/enlazarPautasGrupo/<int:idGroup>', methods=['GET', 'POST'])
def linkPatternsGroup(idGroup):
    form = SearchPatternsForm(current_user.get_id())
    form2 = PaginationForm(1)

    cursorGroup = mongoClient["groups"].find_one({"therapist":current_user.get_id(), "id": idGroup})

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"]}

    rowsBreadCrumb = [{"href": "/", "name":"Inicio"}, {"href": "/verGrupos", "name":"Ver grupos"}, \
        {"href": "/verGrupo/" + str(idGroup), "name": cursorGroup["name"]}]


    #Link patterns to group
    if request.args.get("pattIds") is not None:
        pattIds = list(map(int, request.args.get("pattIds").split(",")))
        mongoClient["groups"].update_one({"id":idGroup}, {"$push": {"patterns":{"$each" : pattIds}} })
        flash("Pautas vinculadas al grupo correctamente", "success")
        return redirect(urlPrefix + url_for('groups.viewGroup', idGroup=idGroup))

    if form.validate_on_submit() is False:
        form.name.data = ""
        form.patients.data = []
        form.groups.data = []
        form.intensities.data = []
        form.pageNumber.data = "1"

    queryResult = searchPatterns(form, int(form.pageNumber.data), {"type":"groups", "id":idGroup})
    form2 = PaginationForm(queryResult["numberPages"])
    form2.pagination.data = form.pageNumber.data

    return render_template('groups/linkPatternsGroup.html', form=form, form2=form2, rowPatterns=queryResult["rows"], \
        therapistLiteral=therapistLiteral, numberTotalRows=queryResult["numberTotalRows"], \
        numberPages=queryResult["numberPages"], groupInfo=groupInfo, rowsBreadCrumb=rowsBreadCrumb)
        

@login_required
@bp.route('/registrarPautaGrupo/<int:idGroup>', methods=['GET', 'POST'])
def registerPatternGroup(idGroup):
    if mongoClient["groups"].count_documents({"id":idGroup, "therapist":current_user.get_id()}) == 0:
        flash("No existe el grupo especificado", "error")
        return redirect(urlPrefix + url_for('general.index'))
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
            return redirect(urlPrefix + url_for('groups.viewGroup', idGroup=idGroup))
        else:
            flash("El nombre de la pauta debe ser unívoco", "error")

    form = RegisterPatternForm(current_user.get_id())

    groupInfo  = {"id": idGroup, "name":cursorGroup["name"], "description":cursorGroup["description"]}

    return render_template('groups/registerPatternGroup.html', title='Registrar una pauta', form=form, \
        therapistLiteral=therapistLiteral, groupInfo=groupInfo, rowsBreadCrumb=rowsBreadCrumb)
