from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import LoginForm
from app.functions.db import checkUser

#Current role of the person visiting the web
currentRole = 0

@app.route("/")
@app.route("/index")
def index():
    print("[DEBUG] Index")
    global currentRole
    #if(currentRole):
    return render_template("index.html", title="Index", registered={currentRole})
    #else:
    #    print("[DEBUG] Leaving Index")
    #    return redirect("/login", code=302)

@app.route("/login", methods=["GET", "POST"])
def login():
    print("[DEBUG] Login")
    global currentRole
    form = LoginForm()
    if form.validate_on_submit():
        #Validate login
        currentRole = checkUser(form.mail.data, form.password.data)
        print("User role: {}".format(currentRole))
        
        if(currentRole):
            print("[DEBUG] User role: {}".format(currentRole))        
            print("[DEBUG] Leaving Login")
            return redirect(url_for('index'))
            
    #TODO: show some message telling that the user was not found and set form input values to null instead of reloading the page
    return render_template("login.html",  title="Iniciar sesión", form=form)
