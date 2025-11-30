from __future__ import annotations

import asyncio
import dataclasses
from operator import add
from typing import Awaitable, Callable, List, Optional
import time
import sched
import pandas as pd
import logging

from .status import CourseStatusRequester, SessionInfo, SessionStatus


class USNotifier:
    def __init__(self, interval: int, callback: Callable[[List[SessionInfo]], Awaitable[None]]) -> None:
        self.watched_urls = set()
        self.requester = CourseStatusRequester()
        self.current_session_infos = dict()
        self.interval = interval
        self.callback = callback
        self.should_run = True
        self.is_running = False

    def add_watch_url(self, url: str) -> Optional[str]:
        try:
            title = self.requester.get_sport_title(url)
            self.watched_urls.add(url)
            return title
        except:
            return None
    
    async def loop(self):
        while True:
            if not self.should_run:
                await asyncio.sleep(self.interval)

            try:
                for url in self.watched_urls:
                    next_session_infos = self.requester.get_sessions(url)
                    new_available = self.new_available_spots(next_session_infos, url)

                    self.current_session_infos[url] = next_session_infos

                    logging.info(f"New available spots:\n{new_available}")

                    await self.callback(new_available)

            except Exception as e:
                logging.error(f"USNotifier loop error: {e}", exc_info=True)

            logging.info(f"Next call is in {self.interval} seconds")
            await asyncio.sleep(self.interval)

    
    async def start(self):
        self.is_running = True
        await self.loop()

    def stop(self):
        self.should_run = False

    def set_interval(self, interval: int):
        if interval <= 0:
            raise ValueError(f"Interval cannot be negative or 0: given interval is {interval}")

        self.interval = interval

    def new_available_spots(self, next_session_infos: List[SessionInfo], url: str) -> List[SessionInfo]:
        if url not in self.current_session_infos:
            return self.filter_available(next_session_infos)

        session_dicts = list(map(lambda info : dataclasses.asdict(info), self.current_session_infos[url]))
        next_session_dicts = list(map(lambda info : dataclasses.asdict(info), next_session_infos))

        current_df = pd.DataFrame.from_records(session_dicts)
        next_df = pd.DataFrame.from_records(next_session_dicts)

        merged_df = current_df.merge(next_df, on=["day", "datetime", "hour", "sport_title", "room"], suffixes=("_current", "_next"))

        # The new available spots are the ones which were not available previously and are now available
        new_available = merged_df[(merged_df["status_current"] != SessionStatus.AVAILABLE) & 
                                  (merged_df["status_next"] == SessionStatus.AVAILABLE)]
        
        # Drop old informations
        new_available = new_available.drop(columns=["status_current", "num_spots_current"])
        new_available = new_available.rename(columns={"status_next" : "status", "num_spots_next" : "num_spots"})

        new_available_list = list(map(lambda x: SessionInfo(**x), new_available.to_dict("records")))

        return new_available_list

    def filter_available(self, session_infos: List[SessionInfo]) -> List[SessionInfo]:
        return list(filter(lambda info : info.status == SessionStatus.AVAILABLE, session_infos))


