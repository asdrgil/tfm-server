from flask import render_template, url_for, request, flash, redirect
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.views.general import bp
from app.forms import FilterByDateForm, SearchPatientsForm, PaginationForm
from app.mongoMethods import getMultipleEpisodes, getCountMultipleEpisodes, \
    searchPatients
from app.constants import mongoClient, urlPrefix

from datetime import datetime
import time
import math
#import logging
#logging.debug('This is a debug message')


therapistLiteral = ""

@bp.before_request
def before_request():

    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        global therapistLiteral

        therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
            current_user.get_surname2())


'''
@bp.route('/index2', methods=['GET', 'POST'])
@login_required
def index2():

    if request.args.get('noty') is "1":
        flash("Paciente registrado correctamente", "success")

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

        timestampFrom = int(datetime.strptime('{} {}'.format(form.date1.data, form.time1.data), \
            '%Y-%m-%d %H:%M').strftime("%s"))
        timestampTo = int(datetime.strptime('{} {}'.format(form.date2.data, form.time2.data), \
            '%Y-%m-%d %H:%M').strftime("%s"))

        rowEpisodes = getMultipleEpisodes(timestampFrom, timestampTo, idPatient, pageNumber)
        numberTotalRows = getCountMultipleEpisodes(timestampFrom, timestampTo, idPatient)
        numberPages = math.ceil(numberTotalRows/rowsPerPage)

        return render_template('general/viewEpisodesGeneric.html', form=form, \
            therapistLiteral=therapistLiteral, patientInfo=patientInfo, rowEpisodes=rowEpisodes, \
            numberTotalRows=numberTotalRows, numberPages=numberPages)

    return render_template('patients/viewEpisodesGeneric.html', form=form, \
        therapistLiteral=therapistLiteral, patientInfo=patientInfo)
'''

@login_required
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    if request.args.get('noty') is "1":
        flash("Paciente registrado correctamente", "success")

    #Count of the three types of elements for the given therapist
    totalNumberPatients = mongoClient["patients"]\
        .count_documents({"therapist":current_user.get_id()})
    totalNumberPatterns = mongoClient["patterns"]\
        .count_documents({"therapist":current_user.get_id()})
    totalNumberGroups = mongoClient["groups"]\
        .count_documents({"therapist":current_user.get_id()})

    totalNumberElements = {"patients":totalNumberPatients, "patterns":totalNumberPatterns, \
        "groups":totalNumberGroups}


    form = SearchPatientsForm(current_user.get_id())
    form2 = PaginationForm(1)

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

    return render_template('general/index.html', therapistLiteral=therapistLiteral, \
        form=form, form2=form2,  rowPatients=queryResult["rows"], \
        numberPages=queryResult["numberPages"], numberTotalRows=queryResult["numberTotalRows"], \
        totalNumberElements=totalNumberElements)


####################################################################################################

@login_required
@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('general.index'))
    

@bp.route('/tryout')
def tryout():
    return render_template('general/tryout.html')