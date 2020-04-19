from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, IntegerField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, DateField, TimeField
from wtforms.validators import ValidationError, DataRequired, Optional, Email, EqualTo, \
    Length
from app.models import User
from app.constants import maxSelectlength
from pymongo import MongoClient, errors

mongoClient = MongoClient('localhost:27017').tfm

def patientOpts(therapistId):
    cursorPatients = mongoClient["patients"].find({"therapist": therapistId})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    result = []

    for pt in cursorPatients:
        patientString = "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name"))
        
        #Cut the select to maxLength
        if len(patientString) > maxSelectlength:
            patientString = "{} {}, {}.".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")[0])
        
        if len(patientString) > maxSelectlength:
            patientString = "{}. {}., {}.".format(pt.get("surname1")[0], pt.get("surname2")[0], pt.get("name")[0])
        
        #Add padding in case the string is smaller than maxLength        
        patientString = patientString.ljust(maxSelectlength, ' ')
            
    
        row = (str(pt.get("id")), patientString)
        result.append(row)

    return result
    
def patientMinusOpts(therapistId, field, value):
    cursorPatients = mongoClient["patients"].find({"therapist": therapistId, field:{"$ne":value}})\
    .sort([("surname1", 1), ("surname2", 1), ("name", 1)])
    result = []

    for pt in cursorPatients:
        patientString = "{} {}, {}".format(pt.get("surname1"), pt.get("surname2"), pt.get("name"))
        
        #Cut the select to maxLength
        if len(patientString) > maxSelectlength:
            patientString = "{} {}, {}.".format(pt.get("surname1"), pt.get("surname2"), pt.get("name")[0])
        
        if len(patientString) > maxSelectlength:
            patientString = "{}. {}., {}.".format(pt.get("surname1")[0], pt.get("surname2")[0], pt.get("name")[0])
        
        #Add padding in case the string is smaller than maxLength        
        patientString = patientString.ljust(maxSelectlength, ' ')
            
    
        row = (str(pt.get("id")), patientString)
        result.append(row)

    return result

def patternOpts(therapistId):
    cursorPatterns = mongoClient["patterns"].find({"therapist": therapistId}).sort([("name", 1)])
    result = []

    for pt in cursorPatterns:
        row = (str(pt.get("id")), "{}".format(pt.get("name")[:maxSelectlength].ljust(maxSelectlength, ' ')))
        result.append(row)

    return result

def groupOpts(therapistId):
    cursorGroups = mongoClient["groups"].find({"therapist": therapistId}).sort([("name", 1)])
    result = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")[:maxSelectlength].ljust(maxSelectlength, ' ')))
        result.append(row)

    return result
    
def groupMinusOpts(therapistId, field, value):
    cursorGroups = mongoClient["groups"].find({"therapist": therapistId, field:{"$ne":value}})\
        .sort([("name", 1)])
    result = []

    for pt in cursorGroups:
        row = (str(pt.get("id")), "{}".format(pt.get("name")[:maxSelectlength].ljust(maxSelectlength, ' ')))
        result.append(row)

    return result
    



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
    returnBtn = SubmitField('Volver', render_kw={"class":"button is-light", "onclick": "returnPage()", \
        'type':'button'})


    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patients.choices = patientOpts(therapistId)
        self.groups.choices = groupOpts(therapistId)

class PatientSelectForm(FlaskForm):
    patients = SelectMultipleField('Pacientes a enlazar', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    submitBtn = SubmitField('Enlazar', render_kw={"class":"button is-primary", "onclick": "linkPatients()", "type":"button"})
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patients.choices = patientMinusOpts(args[0][0], "patterns", args[0][1])  
        
class GroupSelectForm(FlaskForm):
    groups = SelectMultipleField('Grupos a enlazar', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})
    submitBtn = SubmitField('Enlazar', render_kw={"class":"button is-primary", "onclick": "linkGroups()", "type":"button"})
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groups.choices = groupMinusOpts(args[0][0], "patterns", args[0][1])


class EditPatternForm(FlaskForm):

    name = StringField('Nombre', validators=[DataRequired()], render_kw={"class":"input is-medium", \
        "placeholder":"Nombre de la pauta (obligatorio)", "style":"text-align:center;"})
    description = TextAreaField('Descripción', render_kw={"class":"input is-medium", \
        "placeholder":"Descripción de la pauta (opcional)\n", "style":"text-align:center;width:617px;height:85px"})
    
    intensity1 = BooleanField('Intensidad amarilla')
    intensity2 = BooleanField('Intensidad naranja')
    intensity3 = BooleanField('Intensidad roja')

    patients = SelectMultipleField('Pacientes asociados', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    groups = SelectMultipleField('Grupos asociados', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})

    patternId = HiddenField("patternId")

    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patients.choices = patientOpts(therapistId)
        self.groups.choices = groupOpts(therapistId)


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
    modifyBtn = SubmitField('Modificar datos', \
        render_kw={"class":"button is-primary", "onclick":"submitFunc();", 'type':'button'})
    returnBtn = SubmitField('Volver', \
        render_kw={"class":"button is-light", "onclick": "returnPage()", 'type':'button'})

    gender = RadioField('Género', choices = [('M','Masculino'.ljust(maxSelectlength, ' ')),('F','Femenino'.ljust(maxSelectlength, ' '))], \
        validators=[DataRequired()])

    #Auxiliary variables
    patientId = HiddenField("patientId")
    syncHidden = HiddenField('syncHidden')
    submitType = HiddenField('submitType')
    registrationToken = HiddenField('registrationToken')


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

    gender = RadioField('Género', choices = [('M','Masculino'.ljust(maxSelectlength, ' ')),('F','Femenino'.ljust(maxSelectlength, ' '))], \
        validators=[DataRequired()])
    groups = SelectMultipleField('Grupos de pautas asociados al paciente', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'groupsSelect', 'onchange':'changedSelectGroup();'})
    patterns = SelectMultipleField('Pautas ya creadas asociadas al paciente', validators=[Optional()], \
        choices=[], render_kw={'multiple':'multiple', 'id':'patternsSelect', 'onchange':'changedSelectPattern();'})

    patientId = HiddenField("patientId")
    unlinkPatternId = HiddenField("unlinkPatternId")


    newPatternBtn = SubmitField('Registrar una nueva pauta', render_kw={"class":"button is-link", 'type':'button', \
        "onclick": "newPattern()"})
    linkPatternBtn = SubmitField('Enlazar una pauta ya creada', render_kw={"class":"button is-info", 'type':'button', \
        "onclick": "linkPattern()"})

    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patterns.choices = patternOpts(therapistId)
        self.groups.choices = groupOpts(therapistId)


class RegistrationGroupForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()], render_kw={"class":"input is-medium", \
        "placeholder":"Nombre del grupo (obligatorio)", "style":"text-align:center;"})
    description = TextAreaField('Descripción', validators=[Optional()], render_kw={"class":"input is-medium", \
        "placeholder":"Descripción del grupo (opcional)", "style":"text-align:center;width:617px;height:85px"})

    patterns = SelectMultipleField('Pautas asociadas al grupo (opcional)', validators=[Optional()], \
        choices=[], render_kw={'multiple':'multiple', 'id':'patternsSelect'})

    submit = SubmitField('Registrar grupo', render_kw={"class":"button is-primary"})

    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patterns.choices = patternOpts(therapistId)


class GenericEditForm(FlaskForm):
    saveBtn = SubmitField('Guardar cambios', render_kw={"class":"button is-primary", "onclick": "saveData()", \
        'type':'button'})
    cancelBtn = SubmitField('Cancelar', \
        render_kw={"class":"button is-warning", 'onclick': 'displayModalCancel();','type':'button'})
    deleteBtn = SubmitField('Borrar registro', \
        render_kw={"class":"button is-danger", "onclick": "displayModalDelete()", 'type':'button'})

    viewPatternBtn = SubmitField('Ver pauta', \
        render_kw={"class":"button is-info", 'type':'button'})

    viewGroupBtn = SubmitField('Ver grupo', \
        render_kw={"class":"button is-info", 'type':'button'})

    viewPatientBtn = SubmitField('Ver paciente', \
        render_kw={"class":"button is-info", 'type':'button'})

    returnBtn = SubmitField('Volver', \
        render_kw={"class":"button is-light", "onclick": "returnPage()", 'type':'button'})


class SearchPatternsForm(FlaskForm):
    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Nombre", "style":"text-align:center;width:250px"})
    patients = SelectMultipleField('Pacientes', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    groups = SelectMultipleField('Grupos', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'groupsSelect'})
    intensities = SelectMultipleField('Intensidades', validators=[Optional()], \
        choices=[("1", "Amarilla"), ("2", "Naranja"), ("3", "Roja")], \
        render_kw={'multiple':'multiple', 'id':'intensitiesSelect'})
    searchBtn = SubmitField('Buscar',    render_kw={"class":"button is-primary", "onclick": "saveChanges()"})
    returnBtn = SubmitField('Volver',    render_kw={"class":"button is-light", "onclick": "returnPage()", \
        'type':'button'})

    #Auxiliary variables
    pageNumber = HiddenField("pageNumber")
    submitDone = HiddenField("submitDone")
    deleteId = HiddenField("deleteId")

    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patients.choices = patientOpts(therapistId)
        self.groups.choices = groupOpts(therapistId)



class SearchPatientsForm(FlaskForm):

    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Nombre", "style":"text-align:center;width:250px;"})
    surname1 = StringField('Primer apellido', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Primer apellido", "style":"text-align:center;width:250px;"})
    surname2 = StringField('Segundo apellido', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Segundo apellido", "style":"text-align:center;width:250px;"})
    age = StringField('Edad', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Edad", 'type':'number', 'min':5, 'max':100, \
        "style":"text-align:center;width:250px;"}) 
    genders = SelectMultipleField('Género', validators=[Optional()], choices=[('M','Masculino'.ljust(maxSelectlength, ' ')),('F','Femenino'),
    ], \
        render_kw={'multiple':'multiple', 'id':'gendersSelect'})
    patterns = SelectMultipleField('Pautas asociadas al paciente', validators=[Optional()], choices=[], \
        render_kw={'multiple':'multiple', 'id':'patternsSelect'})
    searchBtn = SubmitField('Buscar', render_kw={"class":"button is-primary"})
    returnBtn = SubmitField('Volver', render_kw={"class":"button is-light", "onclick": "returnPage()", \
        'type':'button'})

    pageNumber = HiddenField("pageNumber")
    submitDone = HiddenField("submitDone")

    deleteId = HiddenField("deleteId")
    deleted = HiddenField("deleted")


    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patterns.choices = patternOpts(therapistId)


class SearchGroupsForm(FlaskForm):
    name = StringField('Nombre', validators=[Optional()], \
        render_kw={"class":"input is-small", "placeholder":"Nombre", "style":"text-align:center;"})
    patients = SelectMultipleField('Pacientes asociados al grupo', validators=[Optional()], choices=patientOpts, \
        render_kw={'multiple':'multiple', 'id':'patientsSelect'})
    patterns = SelectMultipleField('Pautas asociadas al grupo', validators=[Optional()], choices=patternOpts, \
        render_kw={'multiple':'multiple', 'id':'patternsSelect'})
    searchBtn = SubmitField('Buscar',    render_kw={"class":"button is-primary"})

    pageNumber = HiddenField("pageNumber")
    submitDone = HiddenField("submitDone")
    deleteId = HiddenField("deleteId")

    def __init__(self, therapistId: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patients.choices = patientOpts(therapistId)
        self.patterns.choices = patternOpts(therapistId)


class FilterByDateForm(FlaskForm):
    patients = SelectField('Paciente', validators=[Optional()], choices=[], \
        render_kw={'id':'patientsSelect'})

    date1 = StringField('Desde (fecha)', validators=[Optional()], render_kw={"class":"input is-small", \
        "type": "date", "data-display-mode": "inline", "data-is-range":"true", "data-close-on-select":"false", "style":"text-align:center"})
    time1 = StringField('Desde (hora)', validators=[Optional()], render_kw={"class":"input is-small", "type": "time", \
        "data-display-mode": "inline", "style":"text-align:center"})
    date2 = StringField('Hasta (fecha)', validators=[Optional()], render_kw={"class":"input is-small", "type":"date", \
        "data-display-mode": "inline", "data-is-range":"true", "data-close-on-select":"false", "style":"text-align:center"})
    time2 = StringField('Hasta (hora)', validators=[Optional()], render_kw={"class":"input is-small", "type": "time", \
        "data-display-mode": "inline", "data-is-range":"true", "style":"text-align:center"})

    pagination = SelectField('Página', validators=[Optional()], choices=[], \
        render_kw={'id':'paginationSelect', 'onchange':'paginationFunc();'})

    searchBtn = SubmitField('Buscar', render_kw={"class":"button is-primary"})
    searchBtn2 = SubmitField('Buscar', render_kw={"class":"button is-primary", "onclick":"episodesFunc()", "type":"button"})

    submitDone = HiddenField("submitDone")

    def __init__(self, therapistId: int, numberPages: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numberPages = numberPages
        self.patients.choices = patientOpts(therapistId)
        self.pagination.choices = tuple((i,i,) for i in range(1, numberPages+1))

class PaginationForm(FlaskForm):
    pagination = SelectField('Página', validators=[Optional()], choices=[], \
        render_kw={'id':'paginationSelect', 'onchange':'paginationFunc();'})

    def __init__(self, numberPages: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numberPages = numberPages
        self.pagination.choices = tuple((i,i,) for i in range(1, numberPages+1))

class PaginationForm2(FlaskForm):
    pagination = SelectField('Página', validators=[Optional()], choices=[], \
        render_kw={'id':'paginationSelect2', 'onchange':'paginationFunc2();'})

    def __init__(self, numberPages: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numberPages = numberPages
        self.pagination.choices = tuple((i,i,) for i in range(1, numberPages+1))


class TryoutForm(FlaskForm):
    aux = HiddenField("aux")
