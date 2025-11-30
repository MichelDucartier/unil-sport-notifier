from dataclasses import dataclass
from enum import Enum
from http.cookiejar import Cookie
import logging
import re
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import ParseResult, urlparse, urlsplit, urljoin, urlunparse

from requests.sessions import RequestsCookieJar

from .credentials import UserCredentials

class SessionStatus(Enum):
    FULL = "full"
    AVAILABLE = "btn_insc"
    UNAVAILABLE = "close"
    ENROLLED = "in"
    OLD = "old"

@dataclass
class SessionInfo:
    day: str
    datetime: str
    hour: str
    status: SessionStatus
    sport_title: str = ""
    room: str = ""
    num_spots: int = 0

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

    def get_sessions(self, url: str) -> List[SessionInfo]:
        base_url, response = self._request_url(url)
        
        session_infos = self.parse_response(base_url, response)
        
        return session_infos

    def _request_url(self, url: str) -> Tuple[ParseResult, str]:
        self.login()
        base_url = urlparse(url, scheme="path")

        response = self.session.get(url)

        if response.status_code != requests.codes["ok"]:
            logging.warning(f"Request failed for {url} with error {response.text}")

        logging.warning(f"Succesfully requested {url}")

        return base_url, response.text
        
    def _extract_sport_title(self, base_url: ParseResult, response: str) -> Optional[Tuple[str, Tag]]:
        soup = BeautifulSoup(response, "html.parser")
        
        # Extract the "Course" div
        sport = soup.find("dl", attrs={"class" : re.compile(r"nav*")})
        
        if sport is None or sport.find("dt") is None:
            logging.warning(f"No sport found for course: {base_url}! This may indicate a bad parsing")
            return None

        sport_title = sport.find("dt").string or ""

        return sport_title, sport


    def get_sport_title(self, url: str) -> Optional[str]:
        base_url, response = self._request_url(url)
        res = self._extract_sport_title(base_url, response)

        if res is None:
            return None

        title, _ = res

        return title
        
    def parse_response(self, base_url: ParseResult, raw_response: str) -> List[SessionInfo]:
        res = self._extract_sport_title(base_url, raw_response)

        if res is None:
            return []

        session_infos = []

        sport_title, sport = res
        rooms = sport.find_all("dl")
        for room in rooms:
            room_name = room.find("dt").string
            if room_name is None:
                logging.warning(f"No room found")
                return []

            room_name = re.sub("[^A-Za-z0-9 -]", "", room_name)

            course_items = room.find_all("div", {"class": "cours_items"})
            for course_item in course_items:
                # Each course item corresponds to a certain course which happens in the same room
                # Each course can contain many sessions (weekly session for instance)
                session_items = course_item.find_all("div", {"class" : "item"})

                for session_item in session_items:
                    session_info = self.parse_session_info(base_url, session_item)
                    if session_info is None:
                        continue
                    
                    # Update with correct room name
                    session_info.sport_title = sport_title
                    session_info.room = room_name

                    session_infos.append(session_info)

        return session_infos

    def parse_session_info(self, base_url: ParseResult, session_item: BeautifulSoup) -> Optional[SessionInfo]:
        day = session_item.find("span", {"class": "day"}).text
        datetime = session_item.find("span", {"class": "dt"}).text
        hour = session_item.find("span", {"class": "hour"}).text
        status = session_item.find("div", {"class" : "inscr"})

        inner = status.findChild()
        status_string = inner["class"][0]
        status = SessionStatus(status_string)

        num_spots = 0
        if status == SessionStatus.AVAILABLE:
            num_spots = self.get_available_spots(base_url, inner["href"])
        
        return SessionInfo(
                day=day,
                datetime=datetime,
                hour=hour,
                status=status,
                num_spots=num_spots,
        )

    def get_available_spots(self, base_url: ParseResult, relative_href: str) -> int:
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

