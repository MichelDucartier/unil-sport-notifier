from dataclasses import dataclass
from enum import Enum
from http.cookiejar import Cookie
import logging
import re
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import ParseResult, urlparse, urlsplit, urljoin, urlunparse

from requests.sessions import RequestsCookieJar

from .credentials import UserCredentials

class SessionStatus(Enum):
    FULL = "full"
    AVAILABLE = "btn_insc"
    UNAVAILABLE = "close"

@dataclass
class SessionInfo:
    day: str
    datetime: str
    hour: str
    status: SessionStatus
    num_places: int = 0

class CourseStatusRequester:
    SESSION_COOKIE_NAME = "PHPSESSID"
    AUTH_URL = "https://sport.unil.ch/cms_core/auth/login"

    def __init__(self):
        self.session = requests.Session()
        self.credentials = UserCredentials()

        self.session = requests.Session()
                
    def login(self):
        response = self.session.post(CourseStatusRequester.AUTH_URL, 
                     data={"txtLogin" : self.credentials.username, "txtPassword" : self.credentials.password})

        if response.status_code != requests.codes["ok"]:
            logging.warning("Authentication failed")

    def request_url(self, url: str) -> List[SessionInfo]:
        self.login()
        base_url = urlparse(url, scheme="path")

        response = self.session.get(url)

        if response.status_code != requests.codes["ok"]:
            logging.warning(f"Request failed for {url} with error {response.text}")

        logging.warning(f"Succesfully requested {url}")
        session_infos = self.parse_response(base_url, response.text)

        return session_infos

    def parse_response(self, base_url: ParseResult, raw_response: str) -> List[SessionInfo]:
        soup = BeautifulSoup(raw_response, "html.parser")
        course_items = soup.find_all("div", {"class": "cours_items"})

        session_infos = []

        for course_item in course_items:
            # Each course item corresponds to a certain course which happens in the same room
            # Each course can contain many sessions (weekly session for instance)
            session_items = course_item.find_all("div", {"class" : "item"})

            for session_item in session_items:
                session_info = self.parse_session_info(base_url, session_item)
                session_infos.append(session_info)

        return session_infos

    def parse_session_info(self, base_url: ParseResult, session_item: BeautifulSoup) -> SessionInfo:
        day = session_item.find("span", {"class": "day"}).text
        datetime = session_item.find("span", {"class": "dt"}).text
        hour = session_item.find("span", {"class": "hour"}).text
        status = session_item.find("div", {"class" : "inscr"})

        inner = status.findChild()
        status_string = inner["class"][0]
        status = SessionStatus(status_string)
        
        num_places = 0
        if status == SessionStatus.AVAILABLE:
            num_places = self.get_available_places(base_url, inner["href"])

        return SessionInfo(
                day=day,
                datetime=datetime,
                hour=hour,
                status=status,
                num_places=num_places
        )

    def get_available_places(self, base_url: ParseResult, relative_href: str) -> int:
        session_url = urlunparse((
                base_url.scheme,
                base_url.netloc,
                "", "", relative_href.lstrip("?"),
                ""
         ))
        response = self.session.get(session_url)
        
        if response.status_code != requests.codes["ok"]:
            logging.warning(f"Status code is {response.status_code} for url: {session_url}")

        soup = BeautifulSoup(response.text, "html.parser")

        dt_tags = soup.find_all('dt')

        # Loop through them to find the one that starts with "Individuel:"
        for dt in dt_tags:
            if dt.text.strip().startswith("Individuel:"):
                # Extract the number using regex
                match = re.search(r'Individuel:\s*(\d+)', dt.text)
                if match:
                    number = int(match.group(1))
                    return number

        return 0

