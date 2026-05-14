from flask import Flask

from dotenv import load_dotenv
from os import getenv

import database as db

load_dotenv(".env")

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://psql:"+ getenv("PSQL_PW") +"@localhost:5432/pyedb"

admin_email = getenv("ADMIN_EMAIL")
admin_passw = getenv("ADMIN_PW")

db.init(app)

with app.app_context():
  db.create()
  if db.user_exists(admin_email):
    db.db.session.query(db.UsersTable).filter(db.UsersTable.email == admin_email).delete()
    db.db.session.commit()
  db.create_user(
    "admin",        # User firstname, not needed
    "",             # User surname, not needed
    "Admin",        # User type
    admin_passw,         # User password
    admin_email # User email -> main identifier
  )
