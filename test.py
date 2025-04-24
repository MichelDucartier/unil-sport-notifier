import os
from dotenv import load_dotenv
from src.usn.api.status import CourseStatusRequester
from src.usn.api.notifier import USNotifier
import logging

import discord
from src.usn.discord.client import USNDiscordBot
from src.usn.discord.credentials import DiscordCredentials

logging.basicConfig(filename="notifier.log", level=logging.INFO)

# status = CourseStatusRequester()
# sesison_infos = status.request_url(url="https://sport.unil.ch/?pid=80&aid=58#content")
# 
# print(sesison_infos)

# notifier = USNotifier(interval=0)
# notifier.add_watch_url("https://sport.unil.ch/?pid=80&aid=58#content")
# print(notifier.watched_urls)
# 
# notifier.loop()

intents = discord.Intents.default()
intents.message_content = True

client = USNDiscordBot(intents=intents)
credentials = DiscordCredentials()
client.run(credentials.token)

