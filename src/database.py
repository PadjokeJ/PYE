from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import ForeignKey, Integer, String
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
  comments: Mapped[List[str]] = mapped_column(JSON)
  student: Mapped["StudentData"] = relationship(back_populates="courses")
  subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
  subject: Mapped["Subject"] = relationship(back_populates="students")

class Subject(Base):
  __tablename__ = "subject"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher.id"))
  students: Mapped[List["StudentCourse"]] = relationship(back_populates="subject")
  teacher: Mapped["Teacher"] = relationship(back_populates="subjects")

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
  return db.session.execute(db.select(UsersTable).order_by(UsersTable.email))

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

def get_student_id(name: str) -> str:
  with open("db/student_ids.json", 'r') as f:
    students = json.load(f)
  return students[name.lower()]
 
def get_students() -> dict:
  with open("db/students.json", 'r') as f:
    students = json.load(f)
  return students

def student_data(sid: str) -> dict:
  students = get_students()
  return students[sid]

def student_name_to_data(name: str) -> dict:
  sid = get_student_id(name)
  return student_data(sid)

def create_user(name: str, surname: str, utype: str, pw: str, email: str):
  n = name.lower()
  s = surname.lower()

  passw = bytes(pw, "utf-8")

  salt = password.generate_random_salt(64)
  pwdh, salt = password.salt(passw, salt)

  hpw = password.hash(pwdh)

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
  user.reset = False

  db.session.commit()

def get_deprecation(user: str) -> bool:
  return get_user(user).reset
