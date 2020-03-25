from flask import render_template, flash, redirect, url_for
from flask_login import login_user, current_user, login_required
from app import db
from app.forms import LoginForm, RegisterTherapistForm
from app.models import User
from app.views.auth import bp
from app.constants import urlPrefix

@bp.route('/iniciarSesion', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        flash(u'Ya hay una sesión activa', 'info')
        return redirect(urlPrefix + url_for('general.index'))
    
    form = LoginForm()
    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(u'Usuario o contraseña inválidos', 'error')
            return redirect(urlPrefix + url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        flash(u'Has iniciado sesión correctamente', 'success')
        return redirect(urlPrefix + url_for('general.index'))
    else:
        flash(u'No se ha validado el formulario para iniciar sesión', 'error')
    
    return render_template('auth/login.html', title='Iniciar sesión', form=form)
    

@bp.route('/registrarTerapeuta', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash(u'Ya hay una sesión activa', 'info')
        return redirect(urlPrefix + url_for('general.index'))

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
        return redirect(urlPrefix + url_for('auth.login'))
    elif "csrf" in form.errors:
        flash(u'No se ha podido realizar el registro. Pruebe a borrar la caché.', 'error')

    flash(form.errors, "error")

    return render_template('auth/registerTherapist.html', title='Registrar terapeuta', form=form)

