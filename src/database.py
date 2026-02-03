import json
import password

def get_users() -> dict:
  with open("db/users.json", 'r') as f:
    users = json.load(f)
  return users

def get_login(user: str, pw: bytes) -> bool:
  users = get_users()
  
  data = users[password.hash(bytes(user, "utf-8"))]
  salt = bytes(data["salt"], "utf-8")
  pwdh = data["hash"]
  if password.hash(password.salt(pw, salt)[0]) == pwdh:
    return True
  return False
  
def get_type(user: str) -> str:
  users = get_users()

  return users[password.hash(bytes(user, "utf-8"))]["type"]
