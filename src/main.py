from flask import Flask, render_template, request, redirect, url_for
import flask_login
from flask_login import login_required

from dotenv import load_dotenv
from os import getenv
import json

import password
import database

class User(flask_login.UserMixin):
  pass

load_dotenv(".env")

# APP
app = Flask(__name__)
app.secret_key = bytes(str(getenv("SECRET")), "utf-8")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://psql:"+ getenv("PSQL_PW") +"@postgres:5432/pyedb"

# Login manager
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Database
database.init(app)
with app.app_context():
  database.create()

@login_manager.user_loader
def user_loader(email):
  if email == None:
    return
  if not database.user_exists(email):
    return
  
  user = User()
  user.id = email
  user.type = database.get_type(email)
  user.reset = database.get_deprecation(email)

  return user

@login_manager.request_loader
def request_loader(request):
  email = request.form.get("email")
  return user_loader(email)

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "GET":
    if flask_login.current_user.is_authenticated:
      return redirect("/home")
    return render_template("login.html")
  
  email = request.form["email"]
  if database.user_exists(email) and database.get_login(email, bytes(request.form["password"], "utf-8")):
    user = User()
    user.id = email
    user.type = database.get_type(email)
    user.reset = database.get_deprecation(email)
    flask_login.login_user(user)
    if user.reset:
      token = str(password.generate_random_salt(64))[2:-1]

      return redirect("/reset/" + token)
    return redirect("/home")
  return redirect("/login?wrong")

@app.route("/logout")
@login_required
def logout():
  flask_login.logout_user()
  return redirect("/login")

@app.route("/")
def root():
  if flask_login.current_user.is_authenticated:
    return redirect("/home")
  return redirect("/login")

@app.route("/home")
@login_required
def home():
  return render_template("home.html")

@app.route("/grades")
@login_required
def grades():
  if flask_login.current_user.type == "Parent" or flask_login.current_user.type == "Teacher":
    return render_template("grades.html")
  return redirect("/home")

@app.route("/grade/<student>")
@login_required
def grade(student):
  if flask_login.current_user.type == "Teacher":
    return render_template("grade_directory.html")
  return redirect("/grades")

@app.route("/feedback")
@login_required
def feedback():
  if flask_login.current_user.type == "Parent" or flask_login.current_user.type == "Teacher":
    return render_template("feedback.html")
  return redirect("/home")

@app.route("/reset/<token>", methods=["GET", "POST"])
@login_required
def reset_pass(token=None):
  if token == None:
    return redirect("/logout") # this should probably give 404

  if flask_login.current_user.reset == False:
    return redirect("/home")

  if request.method == "POST":
    if request.form["password"] != request.form["confirm"]:
      return redirect("/reset/" + token)
    
    flask_login.current_user.reset = False

    database.update_password(flask_login.current_user.id, request.form["password"])
    return redirect("/home")

  return render_template("reset.html")

@app.route("/admin")
@login_required
def admin():
  if flask_login.current_user.type != "Admin":
    return redirect("/home")

  return render_template("admin.html")

@app.route("/add-user", methods=["GET", "POST"])
@login_required
def create_user():
  if flask_login.current_user.type != "Admin":
    return redirect("/home")
  
  if request.method == "GET":
    return redirect("/admin?success")
  
  name = request.form["name"]
  surname = request.form["surname"]

  utype = request.form["type"]

  email = request.form["email"]
  passw = request.form["password"]

  database.create_user(name, surname, utype, passw, email)

  return redirect("/admin?success")

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080, debug=True)

