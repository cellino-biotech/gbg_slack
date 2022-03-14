import os
import json
import dotenv
import polling

from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


PATH_ENV = Path(".") / ".env"
dotenv.load_dotenv(dotenv_path=PATH_ENV)

last_event_data = None

url = f"postgresql://{os.environ['DB_USERNAME']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Events(db.Model):
    __tablename__ = "Events"
    EventId = db.Column(db.Integer, primary_key=True)
    Data = db.Column(db.String())
    Topic = db.Column(db.String())
    Start = db.Column(db.DateTime(timezone=True))
    End = db.Column(db.DateTime(timezone=True))


def query_status_event():
    global last_event_data

    event = (
        Events.query.filter_by(
            Topic="Biosero.DataModels.Events.ModuleStatusUpdateEvent"
        )
        .order_by(Events.Start.desc())
        .first()
    )

    data = json.loads(event.Data)

    if data != last_event_data:
        print(data["Capabilities"])
        last_event_data = data


polling.poll(lambda: query_status_event(), step=5, poll_forever=True)
