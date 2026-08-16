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
  user.data = database.get_user(email)

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
  return render_template("home.html", username=database.get_user(flask_login.current_user.id).firstname)

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

  return render_template("admin.html", students=database.all_students())

@app.route("/users")
@login_required
def users_dash():
  if flask_login.current_user.type != "Admin":
    return redirect("/home")
  return render_template("users.html", users=database.get_users(), students=database.all_students())

@app.route("/update-user", methods=["POST", "GET"])
@login_required
def user_pass():
  email = request.form["email"]
  if flask_login.current_user.type != "Admin":
    return redirect("/home")
  
  if request.method == "GET":
    return redirect("/users")
  database.update_password(str(email), request.form["password"])
  return redirect("/users?success")

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

  stud_id = 0

  if utype == "Parent":
    stud_id = request.form["student_id"]

  database.create_user(name, surname, utype, passw, email, stud_id)

  return redirect("/admin?success")

@app.route("/privacy-policy")
def privacy_policy():
  return render_template("privacy.html")

@app.route("/add-child/<parent_id>/<child_id>", methods=["POST"])
@login_required
def add_child(parent_id: str, child_id: int):
  if flask_login.current_user.type != "Admin":
    return "not an admin", 403

  database.add_child(parent_id, child_id)

  return "added child"

@app.route("/new-course")
@login_required
def dash_create_course():
  if flask_login.current_user.type != "Teacher":
    return redirect("/home")
  
  return render_template("new_course.html")

@app.route("/add-course", methods=["GET", "POST"])
@login_required
def create_course():
  if flask_login.current_user.type != "Teacher":
    return redirect("/home")
  
  if request.method == "GET":
    return redirect("/new-course?success")
  
  name = request.form["name"]
  grade = request.form["grade"]

  color = 0;

  if "color" in request.form.keys():
    color = int(request.form["color"][1:], 16)

  database.create_course(flask_login.current_user.id, name, grade, color)

  return redirect("/new-course?success")

@app.route("/courses")
@login_required
def course_access():
  courses = database.get_courses(flask_login.current_user.id) # TODO : parents access

  return render_template("courses.html", courses=courses)

@app.route("/courses/<course_id>")
@login_required
def get_course(course_id: str):
  courses = database.get_courses(flask_login.current_user.id)
  course = database.get_course(str(course_id))
  if (course == None or not course in courses):
    return redirect("/courses")
  return render_template("course.html", course=course, all_students=database.all_students())

@app.route("/courses/<course_id>/<stud_id>")
@login_required
def get_course_student(course_id: str, stud_id: str):
  if not flask_login.current_user.type == "Teacher":
    return redirect("/course/" + str(course_id))

  course = database.get_course(str(course_id))
  stud   = database.get_student_course(str(stud_id))

  if not stud in course.students:
    return redirect("/course/" + str(course_id))

  return render_template("student.html", student=stud)

@app.route("/student/module/<mod_id>", methods=["POST", "GET"])
@login_required
def update_student_module_progress(mod_id: str):
  module = database.get_student_module(str(mod_id))

  if request.method == "GET":
    return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}?success")

  if not module.subject.subject.teacher.user.email == flask_login.current_user.id:
    return redirect("/courses")

  opt = True if "optional" in request.form.keys() and request.form["optional"] == "optional" else False
  pas = True if "passed" in request.form.keys() and request.form["passed"] == "passed" else False
  foc = True if "focussed" in request.form.keys() and request.form["focussed"] == "focussed" else False

  pro = 0
  if "progress" in request.form.keys():
    try:
      pro = int(request.form["progress"])
    except:
      pro = 0

  database.modify_student_module(str(mod_id), opt, pro, pas, foc)

  return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}?success")

@app.route("/student/category/<cat_id>", methods=["POST", "GET"])
@login_required
def update_student_category_progress(cat_id: str):
  cat = database.get_student_category(str(cat_id))
  module = cat.student_module

  if request.method == "GET":
    return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}?success")

  if not module.subject.subject.teacher.user.email == flask_login.current_user.id:
    return redirect("/courses")

  opt = True if "optional" in request.form.keys() and request.form["optional"] == "optional" else False

  pro = 0
  if "progress" in request.form.keys():
    try:
      pro = int(request.form["progress"])
    except:
      pro = 0

  pas = True if "passed" in request.form.keys() and request.form["passed"] == "passed" else False

  database.modify_student_category(str(cat_id), opt, pro, pas)

  return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}?success")

@app.route("/add-to-course/<course_id>", methods=["POST", "GET"])
@login_required
def add_to_course(course_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")
  if request.method == "POST":
    database.add_student_to_course(str(course_id), request.form["student"])
    return redirect("/courses/" + str(course_id))
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/add-course-module/<course_id>", methods=["POST", "GET"])
@login_required
def add_course_module(course_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")
  if request.method == "POST":
    database.add_course_module(str(course_id), request.form["title"])
    return redirect("/courses/" + str(course_id))
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/add-module-category/<course_id>/<module_id>/", methods=["POST", "GET"])
@login_required
def add_module_category(course_id: str, module_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")

  if request.method == "POST":
    database.add_module_category(str(module_id), str(course_id), request.form["title"])
    return redirect("/courses/" + str(course_id))
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/hide-course/<course_id>", methods=["POST"])
@login_required
def hide_student_course(course_id: str):
  student_course = database.get_student_course(str(course_id))
  if flask_login.current_user.type != "Teacher" or flask_login.current_user.id != student_course.subject.teacher.user_email:
    return redirect(f"/courses/{student_course.subject_id}/{student_course.id}")
  
  database.hide_student_course(str(course_id), request.form.get("hide") == "true")

  return redirect(f"/courses/{student_course.subject_id}/{student_course.id}?success")

def is_correct_teacher(course_id: str) -> bool:
  return flask_login.current_user.type == "Teacher" and flask_login.current_user.id == database.get_course(course_id).teacher.user_email

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080, debug=True)

