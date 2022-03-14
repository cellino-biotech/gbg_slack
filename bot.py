import os
import json
import flask
import slack
import dotenv
import polling

from pathlib import Path
from flask import Flask, Response
from flask_sqlalchemy import SQLAlchemy
from slackeventsapi import SlackEventAdapter
from threading import Thread


# point to local .env file for environment variables
PATH_ENV = Path(".") / ".env"
dotenv.load_dotenv(dotenv_path=PATH_ENV)

# create url to sql database
db_credentials = f"{os.environ['DB_USERNAME']}:{os.environ['DB_PASSWORD']}"
db_target = f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
db_url = "postgresql://" + db_credentials + db_target

# configure flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # suppress warning
db = SQLAlchemy(app)

# configure event handler
slack_event_adapter = SlackEventAdapter(
    os.environ["SIGNING_SECRET"], "/slack/events", app
)

client = slack.WebClient(token=os.environ["SLACK_TOKEN"])
BOT_ID = client.api_call("auth.test")["user_id"]

gbg_updates_channel_id = "C02FK1F5CUQ"
last_event_data = None
message_counts = {}


class Events(db.Model):
    """Database mapping for SQLAlchemy queries"""

    __tablename__ = "Events"
    EventId = db.Column(db.Integer, primary_key=True)
    Data = db.Column(db.String())
    Topic = db.Column(db.String())
    Start = db.Column(db.DateTime(timezone=True))
    End = db.Column(db.DateTime(timezone=True))


class EventUpdate:
    """Message formatting for database event updates"""

    def __init__(self, channel, data):
        self.channel = channel
        self.data = data

        self.text = "*Capabilities*\n"

        for cap in self.data:
            self.text = self.text + f"- {cap}\n"

        self.text = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (self.text),
            },
        }
        self.divider = {"type": "divider"}

    def get_message(self):
        return {"channel": self.channel, "blocks": [self.text, self.divider]}


def send_event_update(channel, data):
    event_update = EventUpdate(channel, data)
    message = event_update.get_message()
    client.chat_postMessage(**message)


@slack_event_adapter.on("message")
def message(payload):
    event = payload.get("event", {})
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")

    if user_id != BOT_ID:
        client.chat_postMessage(channel=channel_id, text="hello :robot_face:")


@app.route("/message-count", methods=["POST"])
def message_count():
    data = flask.request.form
    user_id = data.get("user_id")
    channel_id = data.get("channel_id")
    message_count = message_counts.get(user_id, 0)
    client.chat_postMessage(channel=channel_id, text=f"Message count: {message_count}")

    # status code 200 == OK
    return Response(), 200


@app.route("/event", methods=["POST"])
def latest_event():
    data = flask.request.form
    user_id = data.get("user_id")
    channel_id = data.get("channel_id")

    event = Events.query.filter_by(
        Topic="Biosero.DataModels.Events.ModuleStatusUpdateEvent"
    )
    print(event)

    # status code 200 == OK
    return Response(), 200


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
        send_event_update(gbg_updates_channel_id, data["Capabilities"])
        last_event_data = data


def poll_database():
    polling.poll(lambda: query_status_event(), step=30, poll_forever=True)


if __name__ == "__main__":
    # thread the polling function, otherwise flask will be overwhelmed
    poll = Thread(target=poll_database, daemon=True)
    poll.start()
    app.run(debug=True)
