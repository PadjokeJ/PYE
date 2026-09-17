from flask import Flask, render_template, request, redirect, url_for
import flask_login
from flask_login import login_required
from flask_mail import Mail, Message

from dotenv import load_dotenv
from os import getenv
import json

import re

import password
import database

class User(flask_login.UserMixin):
  pass

load_dotenv(".env")

# APP
app = Flask(__name__)
app.secret_key = bytes(str(getenv("SECRET")), "utf-8")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://psql:"+ getenv("PSQL_PW") +"@" + getenv("PSQL_HOSTNAME") + ":5432/pyedb"

# Mail
mail_user = str(getenv("SERVICE_EMAIL"))
admin_email = str(getenv("ADMIN_EMAIL"))
app.config["MAIL_SERVER"] = str(getenv("SERVICE_SERVER"))
app.config["MAIL_PORT"] = int(getenv("SERVICE_PORT"))
app.config["MAIL_USERNAME"] = mail_user
app.config["MAIL_PASSWORD"] = str(getenv("SERVICE_EMAIL_PASSWORD"))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
mail = Mail(app)

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
  return render_template("home.html.j2", username=database.get_user(flask_login.current_user.id).firstname)

@app.route("/feedback")
@login_required
def feedback():
  if flask_login.current_user.type == "Parent" or flask_login.current_user.type == "Teacher":
    return render_template("feedback.html.j2")
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

    msg = Message(
      subject="PYE: Votre compte vient d'être mis à jour",
      recipients=[flask_login.current_user.id],
      sender=("PYE", mail_user),
      reply_to=admin_email,
      body=f"Votre mot de passe du compte sur { request.host_url } a été modifié.\n\nSi ce n'était pas vous, vous pouvez écrire à votre administateur { admin_email }, ou répondre à ce mail\n\nCeci est un mail automatique.",
    )

    mail.send(msg)

    return redirect("/home")

  return render_template("reset.html")

@app.route("/admin")
@login_required
def admin():
  if flask_login.current_user.type != "Admin":
    return redirect("/home")

  return render_template("admin.html.j2", students=database.all_students())

@app.route("/users")
@login_required
def users_dash():
  if flask_login.current_user.type != "Admin":
    return redirect("/home")
  return render_template("users.html.j2", users=database.get_users(), students=database.all_students())

@app.route("/update-user", methods=["POST", "GET"])
@login_required
def user_pass():
  email = request.form["email"]
  if flask_login.current_user.type != "Admin":
    return redirect("/home")
  
  if request.method == "GET":
    return redirect("/users")
  database.update_password(str(email), request.form["password"])

  msg = Message(
    subject="PYE: Votre compte vient d'être mis à jour",
    recipients=[email],
    sender=("PYE", mail_user),
    body=f"Votre mot de passe du compte sur { request.host_url } a été modifié par un administrateur.\n\nVous pouvez vous connecter avec le mot de passe :\n\n{ request.form["password"] }\n\nCeci est un mail automatique, veuillez ne pas y répondre.",
  )

  mail.send(msg)

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

  msg = Message(
    subject="PYE: Votre nouveau compte",
    recipients=[email],
    sender=("PYE", mail_user),
    body=f"Votre compte sur { request.host_url } a été créé par votre administrateur { admin_email }.\n\nVous pouvez vous connecter avec votre addresse { email } et le mot de passe :\n\n{ passw }\n\nCeci est un mail automatique, veuillez ne pas y répondre.",
  )

  mail.send(msg)

  return redirect("/admin?success")

@app.route("/privacy-policy")
def privacy_policy():
  return render_template("privacy.html.j2")

@app.route("/add-child/<parent_id>/<child_id>", methods=["POST"])
@login_required
def add_child(parent_id: str, child_id: int):
  if flask_login.current_user.type != "Admin":
    return "not an admin", 403

  database.add_child(parent_id, child_id)

  return "added child", 200

@app.route("/new-course")
@login_required
def dash_create_course():
  if flask_login.current_user.type != "Teacher":
    return redirect("/home")
  
  return render_template("new_course.html.j2")

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
  if flask_login.current_user.type != "Parent":
    courses = database.get_courses(flask_login.current_user.id)
  else:
    courses = database.get_child_courses(flask_login.current_user.id)

  return render_template("courses.html.j2", courses=courses)

@app.route("/courses/<course_id>")
@login_required
def get_course(course_id: str):
  subject = database.get_course(str(course_id))
  match flask_login.current_user.type:
    case "Teacher":
      course = subject
    case "Student":
      for sc in subject.students:
        if sc.student.user_email == flask_login.current_user.id:
          course = sc
    case "Parent":
      for s in subject.students:
        if str(s.student.id) in database.get_user(flask_login.current_user.id).student_id:
          course = s
    case _:
      return "You can't access this course", 403
  
  return render_template("course.html.j2", course=course, all_students=database.all_students())

@app.route("/courses/<course_id>/title/<color>/<title>", methods=["GET", "POST"])
@login_required
def modify_course_title(course_id: str, color: str, title: str):
  courses = database.get_courses(flask_login.current_user.id)
  course = database.get_course(str(course_id))

  if not flask_login.current_user.type == "Teacher":
    return redirect("/course/" + str(course_id))

  if course == None or not course in courses or request.method == "GET":
    return redirect("/courses/" + course_id)

  if not re.search("([0-9]|[a-f]){6}", color):
    return "Not a color", 400

  database.modify_course_title(course_id, int(color, 16), title)
  
  return render_template("course.html.j2", course=course, all_students=database.all_students())

@app.route("/courses/<course_id>/<stud_id>", methods=["GET"])
@login_required
def get_course_student(course_id: str, stud_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/course/" + str(course_id))

  course = database.get_course(str(course_id))
  stud   = database.get_student_course(str(stud_id))

  if not stud in course.students:
    return redirect("/course/" + str(course_id))

  return render_template("student.html.j2", student=stud)

@app.route("/students", methods=["GET"])
@login_required
def get_child_students():
  if flask_login.current_user.type != "Parent":
    return "You don't have access to this page", 403

  children = database.get_children(flask_login.current_user.id)

  return render_template("students.html.j2", students=children)

@app.route("/courses/<course_id>/<stud_id>", methods=["DELETE"])
@login_required
def del_course_student(course_id: str, stud_id: str):
  if not is_correct_teacher(course_id):
    return "forbidden", 403
  database.del_from_course(course_id, stud_id)
  return "removed student", 200

@app.route("/courses/<course_id>/<stud_id>/<cat_id>")
@login_required
def get_course_student_category(course_id: str, stud_id: str, cat_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/course/" + str(course_id))

  course = database.get_course(str(course_id))
  stud   = database.get_student_course(str(stud_id))
  catego = database.get_student_module(str(cat_id))

  if not stud in course.students:
    return redirect("/course/" + str(course_id))

  return render_template("category.html.j2", student=stud, category=catego)

@app.route("/student/module/<mod_id>", methods=["POST", "GET"])
@login_required
def update_student_module_progress(mod_id: str):
  module = database.get_student_module(str(mod_id))

  if request.method == "GET":
    return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}/{module.id}?success")

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

  return redirect(f"/courses/{module.subject.subject.id}/{module.student_course_id}/{module.id}?success")

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
  foc = True if "focussed" in request.form.keys() and request.form["focussed"] == "focussed" else False

  database.modify_student_category(str(cat_id), opt, pro, pas, foc)

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

@app.route("/del-module-category/<course_id>/<module_id>/<category_id>/", methods=["DELETE"])
@login_required
def del_module_category(course_id: str, module_id: str, category_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")

  if request.method == "DELETE":
    database.del_module_category(str(category_id))
    return "deleted", 200
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/del-module/<course_id>/<module_id>/", methods=["DELETE"])
@login_required
def del_module(course_id: str, module_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")

  if request.method == "DELETE":
    database.del_module(str(module_id))
    return "deleted", 200
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/add-module-category/<course_id>/<module_id>/", methods=["POST", "GET"])
@login_required
def add_module_category(course_id: str, module_id: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")

  if request.method == "POST":
    database.add_module_category(int(module_id), str(course_id), request.form["title"])
    return redirect("/courses/" + str(course_id))
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/edit-module-category/<course_id>/<category_id>/title/<title>", methods=["PUT", "GET"])
@login_required
def mod_module_category_title(course_id: int, category_id: int, title: str):
  if not is_correct_teacher(course_id):
    return redirect("/courses/" + str(course_id) + "?auth=False")

  if request.method == "PUT":
    database.edit_module_category_title(int(category_id), str(title))
    return "edited with success", 200
  return redirect("/courses/" + str(course_id) + "?success")

@app.route("/hide-course/<course_id>", methods=["POST"])
@login_required
def hide_student_course(course_id: str):
  student_course = database.get_student_course(str(course_id))
  if flask_login.current_user.type != "Teacher" or flask_login.current_user.id != student_course.subject.teacher.user_email:
    return redirect(f"/courses/{student_course.subject_id}/{student_course.id}")
  
  database.hide_student_course(str(course_id), request.form.get("hide") == "true")

  return redirect(f"/courses/{student_course.subject_id}/{student_course.id}?success")

@app.route("/comments/<student_id>", methods=["POST", "DELETE", "GET"])
@login_required
def update_student_comments(student_id: int):
  course = database.get_student_course(student_id).subject

  if not is_correct_teacher(course.id):
    return "Not allowed to modify comments", 403
  
  if request.method == "POST":
    if not "comment" in request.form.keys():
      return "comment is empty", 400
    database.add_comment(student_id, request.form["comment"])
  elif request.method == "DELETE":
    if not "comment_id" in request.form.keys():
      return "no comment id provided", 400
    database.del_comment(student_id, request.form["comment_id"])
  else:
    return redirect(f"/courses/{course.id}/{student_id}?success")
  
  return redirect(f"/courses/{course.id}/{student_id}?success")

def is_correct_teacher(course_id: str) -> bool:
  return flask_login.current_user.type == "Teacher" and flask_login.current_user.id == database.get_course(course_id).teacher.user_email

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8080, debug=True)

