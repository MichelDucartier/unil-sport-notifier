from dotenv import load_dotenv
import os

"""
Trust me
"""
class UserCredentials:
    USERNAME_KEY = "APP_USERNAME"
    PASSWORD_KEY = "APP_PASSWORD"

    def __init__(self) -> None:
        load_dotenv()

        self.username = os.getenv(UserCredentials.USERNAME_KEY, "")
        self.password = os.getenv(UserCredentials.PASSWORD_KEY, "")
        
