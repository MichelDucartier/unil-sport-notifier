import os
from dotenv import load_dotenv
from src.usn.api.status import CourseStatusRequester
from src.usn.api.notifier import USNotifier
import logging

import discord
from src.usn.discord.client import USNDiscordBot
from src.usn.discord.credentials import DiscordCredentials

logging.basicConfig(filename="notifier.log", level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

client = USNDiscordBot(intents=intents)
credentials = DiscordCredentials()
client.run(credentials.token)

