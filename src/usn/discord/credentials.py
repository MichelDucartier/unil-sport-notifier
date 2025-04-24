from dotenv import load_dotenv
import os

"""
Trust me
"""
class DiscordCredentials:
    DISCORD_TOKEN_KEY = "DISCORD_TOKEN"

    def __init__(self) -> None:
        load_dotenv()

        self.token = os.getenv(DiscordCredentials.DISCORD_TOKEN_KEY, "")
 
