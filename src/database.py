from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship

from sqlalchemy.types import JSON

from typing import List, Optional

import json
import password

class Base(DeclarativeBase):
  ...

class Teacher(Base):
  __tablename__ = "teacher"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_email: Mapped[str] = mapped_column(ForeignKey("users.email"))
  subjects: Mapped[List["Subject"]] = relationship(back_populates="teacher")
  user: Mapped["UsersTable"] = relationship(back_populates="teacher_data")

class StudentData(Base):
  __tablename__ = "students"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  courses: Mapped[List["StudentCourse"]] = relationship(back_populates="student")
  user: Mapped["UsersTable"] = relationship(back_populates="student_data")
  user_email: Mapped[str] = mapped_column(ForeignKey("users.email"))

class StudentCourse(Base):
  __tablename__ = "student_course"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  data_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
  progress: Mapped[int] = mapped_column(Integer)
  hidden: Mapped[bool] = mapped_column(Boolean)
  comments: Mapped[List[str]] = mapped_column(JSON)
  student: Mapped["StudentData"] = relationship(back_populates="courses")
  subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
  subject: Mapped["Subject"] = relationship(back_populates="students")
  modules: Mapped[List["StudentModule"]] = relationship(back_populates="student_course")

class StudentModule(Base):
  __tablename__ = "student_module"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  subject: Mapped["SubjectModule"] = relationship(back_populates="student_modules")
  subject_id: Mapped[int] = mapped_column(ForeignKey("module.id"))

  optional: Mapped[bool] = mapped_column(Boolean)
  progress: Mapped[int] = mapped_column(Integer)
  passed: Mapped[bool] = mapped_column(Boolean)

  student_course: Mapped["StudentCourse"] = relationship(back_populates="modules")
  student_course_id: Mapped[int] = mapped_column(ForeignKey("student_course.id"))

class Subject(Base):
  __tablename__ = "subject"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String)
  grade: Mapped[str] = mapped_column(String)
  teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher.id"))
  students: Mapped[List["StudentCourse"]] = relationship(back_populates="subject")
  teacher: Mapped["Teacher"] = relationship(back_populates="subjects")
  modules: Mapped[List["SubjectModule"]] = relationship(back_populates="subject")

class SubjectModule(Base):
  __tablename__ = "module"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  subject: Mapped["Subject"] = relationship(back_populates="modules")
  subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))

  title: Mapped[str] = mapped_column(String)

  student_modules: Mapped[List["StudentModule"]] = relationship(back_populates="subject")

class UsersTable(Base):
  __tablename__ = "users"

  email: Mapped[str] = mapped_column(primary_key=True)
  salt: Mapped[str] = mapped_column(String)
  hashed: Mapped[str] = mapped_column(String)
  role: Mapped[str] = mapped_column(String)
  reset: Mapped[bool] = mapped_column()
  name: Mapped[str] = mapped_column(String)
  firstname: Mapped[str] = mapped_column(String)

  student_data: Mapped[Optional["StudentData"]] = relationship(back_populates="user")
  teacher_data: Mapped[Optional["Teacher"]] = relationship(back_populates="user")

db = SQLAlchemy(model_class=Base)

def init(app):
  db.init_app(app)

def create():
  db.create_all()

def hash(user: str) -> str:
  return password.hash(bytes(user.lower(), "utf-8"))

def get_users():
  return db.session.query(UsersTable).all()

def get_user(email: str) -> UsersTable:
  return db.session.query(UsersTable).get(email)

def user_exists(email: str) -> bool:
  return get_user(email) != None

def get_login(user: str, pw: bytes) -> bool:
  data = get_user(user)
  
  salt = bytes(data.salt, "utf-8")
  pwdh = data.hashed
  if password.hash(password.salt(pw, salt)[0]) == pwdh:
    return True
  return False
  
def get_type(user: str) -> str:
  return get_user(user).role

def create_user(name: str, surname: str, utype: str, pw: str, email: str):
  n = name.lower()
  s = surname.lower()

  passw = bytes(pw, "utf-8")

  salt = password.generate_random_salt(64)
  pwdh, salt = password.salt(passw, salt)

  hpw = password.hash(pwdh)

  if user_exists(email):
    user = get_user(email)
    user.role = utype
    user.firstname = name
    user.name = name
    user.reset = True
    user.salt = str(salt)[2:-1]
    user.hashed = hpw
    db.session.commit()
    return

  user = UsersTable(
      email=email,
      salt=str(salt)[2:-1],
      hashed=hpw,
      role=utype,
      reset=True,
      name=surname,
      firstname=name
    )

  if utype == "Student":
    user.student_data = StudentData(user_email=email)
  if utype == "Teacher":
    user.teacher_data = Teacher(user_email=email)

  db.session.add(user)
  db.session.commit()

def update_password(email: str, pw: str):
  passw = bytes(pw, "utf-8")

  salt = password.generate_random_salt(64)
  pwdh, salt = password.salt(passw, salt)

  hpw = password.hash(pwdh)

  user = get_user(email)
  user.salt = str(salt)[2:-1]
  user.hashed = hpw
  if user.reset:
    user.reset = False
  else:
    user.reset = True

  db.session.commit()

def get_deprecation(user: str) -> bool:
  return get_user(user).reset

def create_course(owner: str, name: str, grade: str):
  user = get_user(owner)
  subject = Subject(
    teacher=user.teacher_data,
    name=name,
    grade=grade
  )
  db.session.add(subject)
  db.session.commit()

def get_courses(email: str) -> list:
  user_role = get_type(email)
  query = db.session.query(Subject)

  if (user_role == "Teacher"):
    return query.filter(Subject.teacher.has(user_email=email)).all()
  elif (user_role == "Student"):
    student = get_user(email).student_data
    courses = student.courses
    l = []
    for c in courses:
      if not c.hidden:
        l.append(c.subject)

    return l

  return list()

def get_course(id: str) -> Subject:
  return db.session.get(Subject, id)

def get_student_course(id: str) -> StudentCourse:
  return db.session.get(StudentCourse, id)

def get_student_module(id: str) -> StudentModule:
  return db.session.get(StudentModule, id)

def modify_student_module(id: str, optional: bool, progress: int, passed: bool):
  module = get_student_module(id)
  
  module.optional = optional
  module.progress = progress
  module.passed   = passed

  db.session.commit()

  update_progress(module.student_course)

def update_progress(student_course: StudentCourse):
  p = 0
  i = 0
  for module in student_course.modules:
    if not module.optional:
      p += module.progress
      i += 1
  
  student_course.progress = p / i

  db.session.commit()

def all_students() -> list:
  return db.session.query(StudentData).all()

def add_student_to_course(course_id: str, id: str):
  course = get_course(course_id)

  student = db.session.get(StudentData, id)
  
  for s in course.students:
    if str(s.student.id) == id:
      return

  data = StudentCourse(
    data_id=id,
    progress=0,
    subject_id=course_id,
    comments=list(),
    modules=list(),
    hidden=False
  )

  for module in course.modules:
    data.modules.append(StudentModule(
      subject_id=module.id,
      optional=False,
      progress=0,
      passed=False,
      student_course_id=data.id
    ))

  student.courses.append(data)
  course.students.append(data)
  db.session.commit()

def add_course_module(course_id: str, title: str):
  course = get_course(course_id)
  module = SubjectModule(
    subject_id=course_id,
    title=title,
    student_modules=list()
  )
  course.modules.append(module)
  for student in course.students:
    smodule = StudentModule(
      subject_id=module.id,
      optional=False,
      progress=0,
      passed=False,
      student_course_id=student.id
    )
    student.modules.append(smodule)
    update_progress(student)
  db.session.commit()

def hide_student_course(id: str, state: bool):
  sc = get_student_course(id)
  sc.hidden = not sc.hidden
  db.session.commit()

