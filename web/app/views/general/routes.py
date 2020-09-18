from flask import render_template, url_for, request, flash, redirect, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.views.general import bp
from app.forms import FilterByDateForm, SearchPatientsForm, PaginationForm
from app.mongoMethods import getCountMultipleEpisodes, searchPatients, registerTraceUsers
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
        registerTraceUsers(current_user.get_id(), request.endpoint)
        global therapistLiteral

        therapistLiteral = "{} {} {}".format(current_user.get_name(), current_user.get_surname1(), \
            current_user.get_surname2())
    else:
        #Trace for users is not added here because it will be spotted when redirecting the user
        return redirect(urlPrefix + url_for('auth.login'))

@login_required
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    if request.args.get('noty') is "1":
        flash("Paciente registrado correctamente", "success")

    print("[DEBUG] Therapist id:")
    print(current_user.get_id())

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
