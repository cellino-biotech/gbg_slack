import os
import slack
import dotenv

from pathlib import Path


PATH_ENV = Path(".") / ".env"
dotenv.load_dotenv(dotenv_path=PATH_ENV)

client = slack.WebClient(token=os.environ["SLACK_TOKEN"])

client.chat_postMessage(channel="#gbg-updates", text="Hello World!")
