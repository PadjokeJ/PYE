import json
import password

def get_users() -> dict:
  with open("db/users.json", 'r') as f:
    users = json.load(f)
  return users

def get_login(user: str, pw: bytes) -> bool:
  users = get_users()
  
  data = users[user.lower()]
  salt = bytes(data["salt"], "utf-8")
  pwdh = data["hash"]
  if password.hash(password.salt(pw, salt)[0]) == pwdh:
    return True
  return False
  
def get_type(user: str) -> str:
  users = get_users()

  return users[user.lower()]["type"]

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

  uid = password.hash(bytes(email, "utf-8"))
  passw = bytes(pw, "utf-8")

  print(passw)

  data = get_users()

  salt = password.generate_random_salt(64)
  print(salt)
  pwdh, salt = password.salt(passw, salt)

  hpw = password.hash(pwdh)

  user = {
    "salt": str(salt)[2:-1],
    "hash": hpw,
    "type": utype,
    "deprecated": True
  }

  data[uid] = user

  if utype == "Student":
    ...

  with open("db/users.json", 'w') as f:
    json.dump(data, f)

def get_deprecation(usrhash: str) -> bool:
  return "deprecated" in get_users()[usrhash]
