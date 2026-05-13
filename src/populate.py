from flask import Flask

from dotenv import load_dotenv
from os import getenv

import database as db

load_dotenv(".env")

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://psql:"+ getenv("PSQL_PW") +"@localhost:5432/pyedb"

db.init(app)

with app.app_context():
  db.create()
  db.create_user(
    "admin",        # User firstname, not needed
    "",             # User surname, not needed
    "Admin",        # User type
    "1234",         # User password
    "admin@pye.org" # User email -> main identifier
  )

