import os
import slack
import dotenv

from pathlib import Path
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from slackeventsapi import SlackEventAdapter


PATH_ENV = Path(".") / ".env"
dotenv.load_dotenv(dotenv_path=PATH_ENV)

db_url = f"postgresql://{os.environ['DB_USERNAME']}:\
    {os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:\
        {os.environ['DB_PORT']}/{os.environ['DB_NAME']}"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
db = SQLAlchemy(app)

slack_event_adapter = SlackEventAdapter(
    os.environ["SIGNING_SECRET"], "/slack/events", app
)

client = slack.WebClient(token=os.environ["SLACK_TOKEN"])
BOT_ID = client.api_call("auth.test")["user_id"]

message_counts = {}


class WelcomeMessage:
    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.icon_emoji = ":robot_face:"
        self.timestamp = ""
        self.completed = False


@slack_event_adapter.on("message")
def message(payload):
    event = payload.get("event", {})
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")

    if user_id != BOT_ID:
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1


@app.route("/message-count", methods=["POST"])
def message_count():
    data = request.form
    user_id = data.get("user_id")
    channel_id = data.get("channel_id")
    message_count = message_counts.get(user_id, 0)
    client.chat_postMessage(channel=channel_id, text=f"Message count: {message_count}")
    # status code 200 == OK
    return Response(), 200


if __name__ == "__main__":
    app.run(debug=True)
