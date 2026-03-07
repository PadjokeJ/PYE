import json
import password

def get_users() -> dict:
  with open("db/users.json", 'r') as f:
    users = json.load(f)
  return users

def get_login(user: str, pw: bytes) -> bool:
  users = get_users()
  
  data = users[password.hash(bytes(user.lower(), "utf-8"))]
  salt = bytes(data["salt"], "utf-8")
  pwdh = data["hash"]
  if password.hash(password.salt(pw, salt)[0]) == pwdh:
    return True
  return False
  
def get_type(user: str) -> str:
  users = get_users()

  return users[password.hash(bytes(user.lower(), "utf-8"))]["type"]

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
