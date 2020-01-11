from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, IntegerField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, DateField, TimeField
from wtforms.validators import ValidationError, DataRequired, Optional, Email, EqualTo, \
    Length
from app.models import User
from pymongo import MongoClient, errors
#from .mongoMethods import getCurentUser

#TODO: solve it.
therapist = 4

mongoClient = MongoClient('localhost:27017').tfm

class RegisterTherapistForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(message="Este campo es obligatorio.")], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre (obligatorio)", "style":"text-align:center;"})
    surname1 = StringField('Primer apellido', validators=[DataRequired(message="Este campo es obligatorio.")], \
        render_kw={"class":"input is-medium", "placeholder":"Primer apellido (obligatorio)", "style":"text-align:center;"})
    surname2 = StringField('Segundo apellido', render_kw={"class":"input is-medium", \
        "placeholder":"Segundo apellido (opcional)", "style":"text-align:center;"})
    email = StringField('Correo electrónico', validators=[DataRequired(message="Este campo es obligatorio."), \
        Email(message="Debe introducir un correo válido.")], render_kw={"class":"input is-medium", "type": "email", \
        "placeholder":"Correo electrónico (obligatorio)", "style":"text-align:center;"})
    password = PasswordField('Contraseña', validators=[DataRequired(message="Este campo es obligatorio."), \
        Length(min=6, max=20, message="La contraseña debe tener entre 6 y 20 caracteres.")], \
        render_kw={"class":"input is-medium", "type": "password", "placeholder":"Contraseña (obligatorio)", \
        "style":"text-align:center;"})
    password2 = PasswordField('Repite la contraseña', validators=[DataRequired(message="Este campo es obligatorio."), \
        Length(min=6, max=20, message="La contraseña debe tener entre 6 y 20 caracteres."), EqualTo('password', \
            message='Las contraseñas tienen que coincidir')], render_kw={"class":"input is-medium", \
        "type": "password", "placeholder":"Repite la contraseña (obligatorio)", "style":"text-align:center;"})
    submit = SubmitField('Registrar usuario', render_kw={"class":"button is-primary"})
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este correo ya está asociado a una cuenta registrada.')


class LoginForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()], \
        render_kw={"class":"input is-medium", "type": "email", "placeholder":"Correo electrónico (obligatorio)"})
    password = PasswordField('Contraseña', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "type": "password", "placeholder":"Contraseña (obligatorio)"})
    remember_me = BooleanField('Guardar contraseña')
    submit = SubmitField('Iniciar sesión', render_kw={"class":"button is-primary"})

class RegisterPatternForm(FlaskForm):

    name = StringField('Nombre', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre de la pauta (obligatorio)", \
        "style":"text-align:center;"})
    description = TextAreaField('Descripción', \
        render_kw={"class":"input is-medium", "placeholder":"Descripción de la pauta (opcional)\n", \
        "style":"text-align:center;width:617px;height:85px"})
    
    intensity1 = BooleanField('Intensidad amarilla')
    intensity2 = BooleanField('Intensidad naranja')
    intensity3 = BooleanField('Intensidad roja')

    patients = SelectMultipleField('Asociar a pacientes (opcional)', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    groups = SelectMultipleField('Asociar a grupos (opcional)', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})

    submit = SubmitField('Registrar pauta', render_kw={"class":"button is-primary"})


    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.therapistId = therapistId
        self.patients.choices = self.patientOpts()
        self.groups.choices = self.groupOpts()

    def patientOpts(self) -> list:
        cursorPatients = mongoClient["patients"].find({"therapist": self.therapistId})\
        .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
        result = []

        for pt in cursorPatients:
            row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
            result.append(row)

        return result

    def groupOpts(self) -> list:
        cursorGroups = mongoClient["groups"].find({"therapist": self.therapistId, "windowId": {"$exists":False}})\
        .sort([("name", 1)])
        result = []

        for pt in cursorGroups:
            row = (str(pt.get("id")), "{}".format(pt.get("name")))
            result.append(row)

        return result

#TODO: esto se puede mejorar heredando los campos de RegisterPatternForm
class ViewPatternForm(FlaskForm):
    cursorPatients = mongoClient["patients"].find({"therapist": therapist})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    patientOpts = []

    for pt in cursorPatients:
        row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
        patientOpts.append(row)

    cursorGroups = mongoClient["groups"].find({"therapist": therapist, "windowId": {"$exists":False}})\
    .sort([("name", 1)])
    groupOpts = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        groupOpts.append(row)


    name = StringField('Nombre', validators=[DataRequired()], render_kw={"class":"input is-medium", \
        "placeholder":"Nombre de la pauta (obligatorio)", "style":"text-align:center;"})
    description = TextAreaField('Descripción', render_kw={"class":"input is-medium", \
        "placeholder":"Descripción de la pauta (opcional)\n", "style":"text-align:center;width:617px;height:85px"})
    
    intensity1 = BooleanField('Intensidad amarilla')
    intensity2 = BooleanField('Intensidad naranja')
    intensity3 = BooleanField('Intensidad roja')

    patients = SelectMultipleField('Asociar a pacientes (opcional)', validators=[Optional()], choices=patientOpts, \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    groups = SelectMultipleField('Asociar a grupos (opcional)', validators=[Optional()], choices=groupOpts, \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})

    saveBtn = SubmitField('Guardar cambios', \
        render_kw={"class":"button is-primary", "onclick": "displayModalSave(); return false;",'type':'button'})
    cancelBtn = SubmitField('Cancelar', \
        render_kw={"class":"button is-warning", 'onclick': 'displayModalCancel();','type':'button'})
    deleteBtn = SubmitField('Borrar pauta', \
        render_kw={"class":"button is-danger", "onclick": "displayModalDelete()",'type':'button'})

    #Auxiliary variables
    activateEdit = BooleanField('', default=True, \
        render_kw={"class": "switch is-rounded is-info", 'onchange':'changeEditable();'})
    patternId = HiddenField("patternId")


class RegisterPatientForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre", "style":"text-align:center;"})
    surname1 = StringField('Primer apellido', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Primer apellido", "style":"text-align:center;"})
    surname2 = StringField('Segundo apellido (opcional)', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Segundo apellido (opcional)", "style":"text-align:center;"})
    age = IntegerField('Edad', validators=[DataRequired()], render_kw={"class":"input is-medium", \
        "placeholder":"Edad", 'type':'number', 'min':5, 'max':100, "style":"text-align:center;"})
    syncNow = BooleanField('Sincronizar ahora con el dispositivo', default=True, render_kw={"disabled":True})

    cancelBtn = SubmitField('Cancelar', \
        render_kw={"class":"button is-warning", "onclick": "cancelRegister()", "style":"display:none",'type':'button'})
    submitBtn = SubmitField('Registrar paciente', \
        render_kw={"class":"button is-primary", "onclick":"submitFunc();", 'type':'button'})

    gender = RadioField('Género', choices = [('M','Masculino'),('F','Femenino')], validators=[DataRequired()])

    #Auxiliary variables
    syncHidden = HiddenField('syncHidden')
    submitType = HiddenField('submitType')
    registrationToken = HiddenField('registrationToken')
    windowToken = HiddenField("windowToken")


#Add patterns as a subelement of another page
class RegisterPatternForm2(FlaskForm):
    patternName = StringField('Nombre', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre de la pauta", "style":"text-align:center;"})
    patternDescription = TextAreaField('Descripción', render_kw={"class":"input is-medium", \
        "placeholder":"Descripción de la pauta\n", "style":"text-align:center;width:617px;height:85px"})

    patternIntensity1 = BooleanField('Intensidad amarilla')
    patternIntensity2 = BooleanField('Intensidad naranja')
    patternIntensity3 = BooleanField('Intensidad roja')

    patternSubmit = SubmitField('Añadir pauta', \
        render_kw={"class":"button is-link", 'onclick':'insertNewPattern();','type':'button'})


class EditPatientForm(FlaskForm):
    activateEdit = BooleanField('', default=True, \
        render_kw={"class": "switch is-rounded is-info", 'onchange':'changeEditable();'})
    name = StringField('Nombre', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre", "style":"text-align:center;"})
    surname1 = StringField('Primer apellido', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Primer apellido", "style":"text-align:center;"})
    surname2 = StringField('Segundo apellido', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Segundo apellido", "style":"text-align:center;"})
    age = IntegerField('Edad', validators=[DataRequired()], \
        render_kw={"class":"input is-medium", "placeholder":"Edad", "style":"text-align:center;"})

    syncBtn = SubmitField('Sincronizar dispositivo', render_kw={"class":"button is-link", "onclick": "syncDevice()"})

    saveBtn = SubmitField('Guardar cambios', render_kw={"class":"button is-primary", "onclick": "displayModalSave()"})
    cancelBtn = SubmitField('Cancelar', \
        render_kw={"class":"button is-warning", 'onclick': 'displayModalCancel();','type':'button'})
    deleteBtn = SubmitField('Borrar paciente', render_kw={"class":"button is-danger", "onclick":"displayModalDelete()"})

    cursorGroups = mongoClient["groups"].find({"therapist": therapist, "windowId":{"$exists":False}}).sort([("name",1)])
    groupOpts = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        groupOpts.append(row)

    cursorPatterns = mongoClient["patterns"]\
    .find({"therapist": therapist, "windowId": {"$exists":False}}).sort([("name", 1), ("description", 1)])
    patternOpts = []

    for pt in cursorPatterns:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        patternOpts.append(row)

    groups = SelectMultipleField('Grupos de pautas asociados al paciente', validators=[Optional()], choices=groupOpts, \
        render_kw={'multiple':'multiple', 'id':'groupsSelect', 'onchange':'changedSelectGroup();'})
    patterns = SelectMultipleField('Pautas ya creadas asociadas al paciente', validators=[Optional()], \
        choices=patternOpts, \
        render_kw={'multiple':'multiple', 'id':'patternsSelect', 'onchange':'changedSelectPattern();'})

    selectedGroups = HiddenField('selectedGroups')
    cancelScreen = HiddenField('cancelScreen')
    registrationToken = HiddenField('registrationToken')

    #Auxiliary variables
    pattIds = HiddenField("pattIds")
    windowToken = HiddenField("windowToken")
    patientId = HiddenField("patientId")
    synced = HiddenField("synced")


class RegistrationGroupForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()], render_kw={"class":"input is-medium", \
        "placeholder":"Nombre del grupo", "style":"text-align:center;"})
    description = TextAreaField('Descripción', render_kw={"class":"input is-medium", \
        "placeholder":"Descripción del grupo", "style":"text-align:center;width:617px;height:85px"})
    
    selectPatient = RadioField('Pacientes que incluye', choices=[('1','Sí'),('0','No')], default="0", \
        render_kw={"onchange":"selectPatient();"})

    cursorPatients = mongoClient["patients"].find({"therapist": therapist})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    patientOpts = []

    for pt in cursorPatients:
        row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
        patientOpts.append(row)

    cursorPatterns = mongoClient["patterns"].find({"therapist": therapist, "windowId": {"$exists":False}})\
    .sort([("name", 1), ("description", 1)])
    patternOpts = []

    for pt in cursorPatterns:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        patternOpts.append(row)


    patients = SelectMultipleField('Pacientes asociados al grupo', validators=[Optional()], choices=patientOpts, \
        render_kw={'multiple':'multiple', 'id':'patientsSelect', 'onchange':'changedSelectPatient()'})
    patterns = SelectMultipleField('Pautas ya creadas asociadas al grupo', validators=[Optional()], \
        choices=patternOpts, \
        render_kw={'multiple':'multiple', 'id':'patternsSelect', 'onchange':'changedSelectPattern();'})

    #Auxiliary variables
    pattIds = HiddenField('pattIds')
    windowToken = HiddenField("windowToken")
    oldPatterns = HiddenField("oldPatterns")

    submit = SubmitField('Registrar grupo', render_kw={"class":"button is-primary", "onclick":"persistData()"})


class GenericEditForm(FlaskForm):
    activateEdit = BooleanField('', default=True, \
        render_kw={"class": "switch is-rounded is-info", 'onchange':'changeEditable();'})
    saveBtn = SubmitField('Guardar cambios', render_kw={"class":"button is-primary", "onclick": "displayModalSave()"})
    cancelBtn = SubmitField('Cancelar', \
        render_kw={"class":"button is-warning", 'onclick': 'displayModalCancel();','type':'button'})
    deleteBtn = SubmitField('Borrar registro', \
        render_kw={"class":"button is-danger", "onclick": "displayModalDelete()"})


class SearchPatternsForm(FlaskForm):

    cursorPatients = mongoClient["patients"]\
    .find({"therapist":therapist}).sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    patientOpts = []

    for pt in cursorPatients:
        row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
        patientOpts.append(row)

    cursorGroups = mongoClient["groups"].find({"therapist":therapist}).sort([("name", 1)])
    groupOpts = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        groupOpts.append(row)

    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre", "style":"text-align:center;"})
    description = StringField('Descripción', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Descripción", "style":"text-align:center"})
    patients = SelectMultipleField('Pacientes', validators=[Optional()], choices=patientOpts, \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    groups = SelectMultipleField('Grupos', validators=[Optional()], choices=groupOpts, \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})
    intensities = SelectMultipleField('Intensidades', validators=[Optional()], \
        choices=[("1", "Amarilla"), ("2", "Naranja"), ("3", "Roja")], \
        render_kw={'multiple':'multiple', 'id':'intensitiesSelect'})
    searchBtn = SubmitField('Buscar',    render_kw={"class":"button is-primary", "onclick": "saveChanges()"})


class SearchPatientsForm(FlaskForm):
    cursorGroups = mongoClient["groups"].find({"therapist":therapist}).sort([("name", 1)])
    groupOpts = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        groupOpts.append(row)


    cursorPatterns = mongoClient["patterns"].find({"therapist":therapist}).sort([("name", 1), ("description", 1)])
    patternOpts = []

    for pt in cursorPatterns:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        patternOpts.append(row)    

    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre", "style":"text-align:center;"})
    surname1 = StringField('Primer apellido', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Primer apellido", "style":"text-align:center;"})
    surname2 = StringField('Segundo apellido', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Segundo apellido", "style":"text-align:center;"})
    age = StringField('Edad', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Edad", 'type':'number', 'min':5, 'max':100, \
        "style":"text-align:center;"}) 
    groups = SelectMultipleField('Grupos', validators=[Optional()], choices=groupOpts, \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})
    patterns = SelectMultipleField('Pautas ya creadas asociadas al grupo', validators=[Optional()], \
        choices=patternOpts, render_kw={'multiple':'multiple', 'id':'patternsSelect'})
    searchBtn = SubmitField('Buscar',    render_kw={"class":"button is-primary"})


class SearchGroupsForm(FlaskForm):
    cursorPatients = mongoClient["patients"].find({"therapist":therapist})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    patientOpts = []

    for pt in cursorPatients:
        row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
        patientOpts.append(row)

    cursorGroups = mongoClient["groups"].find({}).sort([("name", 1)])
    groupOpts = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        groupOpts.append(row)


    cursorPatterns = mongoClient["patterns"].find({}).sort([("name", 1), ("description", 1)])
    patternOpts = []

    for pt in cursorPatterns:
        row = (str(pt.get("id")), "{}".format(pt.get("name")))
        patternOpts.append(row)    

    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Nombre", "style":"text-align:center;"})
    description = StringField('Descripción', validators=[Optional()], \
        render_kw={"class":"input is-medium", "placeholder":"Descripción", "style":"text-align:center;"})
    patients = SelectMultipleField('Pacientes asociados al grupo', validators=[Optional()], choices=patientOpts, \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    patterns = SelectMultipleField('Pautas asociadas al grupo', validators=[Optional()], choices=patternOpts, \
        render_kw={'multiple':'multiple', 'id':'patternsSelect'})
    searchBtn = SubmitField('Buscar',    render_kw={"class":"button is-primary"})


class FilterByDateForm(FlaskForm):
    cursorPatients = mongoClient["patients"].find({"therapist":therapist})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    patientOpts = []

    for pt in cursorPatients:
        row = (str(pt.get("id")), "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")))
        patientOpts.append(row)

    patients = SelectField('Paciente seleccionado', validators=[Optional()], choices=patientOpts, \
        render_kw={'id':'patientsSelect', 'onchange':"updatePatientValue();"})

    date1 = StringField('Desde (fecha)', validators=[Optional()], render_kw={"class":"input is-medium", \
        "type": "date", "data-display-mode": "inline", "data-is-range":"true", "data-close-on-select":"false"})
    time1 = StringField('Desde (hora)', validators=[Optional()], render_kw={"class":"input is-medium", "type": "time", \
        "data-display-mode": "inline"})
    date2 = StringField('Hasta (fecha)', validators=[Optional()], render_kw={"class":"input is-medium", "type":"date", \
        "data-display-mode": "inline", "data-is-range":"true", "data-close-on-select":"false"})
    time2 = StringField('Hasta (hora)', validators=[Optional()], render_kw={"class":"input is-medium", "type": "time", \
        "data-display-mode": "inline", "data-is-range":"true"})

    searchBtn = SubmitField('Buscar', render_kw={"class":"button is-primary"})

    patientId = HiddenField("patientId")

    def validate(self):
        return True

class TryoutForm(FlaskForm):
    aux = HiddenField("aux")