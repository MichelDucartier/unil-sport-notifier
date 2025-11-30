# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import Intents, Interaction
from typing import Any, Dict, List
import logging
import asyncio

from requests import session

from ..api.notifier import USNotifier
from ..api.status import SessionInfo


import discord
from discord.ext import commands

class USNDiscordBot(commands.Bot):
    def __init__(self, intents: Intents):
        super().__init__(command_prefix="!", intents=intents)
        
        # Mutable state
        self.usnotifier = USNotifier(interval=60, callback=self.send_notification)

        # Setup slash commands
        self.tree.command(name="watch", description="Set a watched course (give the URL)")(self.watch_url)
        self.tree.command(name="setinterval", description="Set an interval")(self.set_interval)
        self.tree.command(name="status", description="Status of the bot")(self.get_status)
        self.tree.command(name="unsubscribe", description="Unsubscribe this channel from every course")(self.unsubscribe)

        self.alert_channel_id = dict()

    async def unsubscribe(self, interaction: Interaction):
        courses = []
        for course, channel_ids in self.alert_channel_id.items():
            if interaction.channel_id in channel_ids:
                self.alert_channel_id[course] = channel_ids.difference({interaction.channel_id})
                courses.append(course)
        
        courses_str = ", ".join(courses)
        await interaction.response.send_message(f"Unsubscribed <#{interaction.channel_id}> from {courses_str}")

    async def get_status(self, interaction: Interaction):
        status = discord.Embed(title="Status", 
                               description=f"Status of USNotifier (pinging every {self.usnotifier.interval} seconds)", 
                               color=0x00ff00)

        for course, channel_ids in self.alert_channel_id.items():
            if len(channel_ids) == 0:
                continue

            channels = "**Subscribed channels**:\n"
            for channel_id in channel_ids:
                channels += f"<#{channel_id}>\n"

            status.add_field(name=course, value=channels, inline=True)

        await interaction.response.send_message(embed=status)


    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        self.loop.create_task(self.usnotifier.start())
        print(f"Logged in as {self.user}")

    async def on_resumed(self):
        logging.info("Bot reconnected — ensuring notifier is running.")

        # If your notifier has a flag to check its state
        if not self.usnotifier.is_running and self.usnotifier.should_run:
            self.loop.create_task(self.usnotifier.start())

    async def watch_url(self, interaction: discord.Interaction, course_url: str):
        title = self.usnotifier.add_watch_url(course_url)
        
        if title is None:
            await interaction.response.send_message(f"Failed to watch {course_url}")
            return

        self.alert_channel_id[title] = \
                self.alert_channel_id.get(title, set()).union({interaction.channel_id})

        await interaction.response.send_message(f"Watching course {course_url} ({title})")

    async def set_interval(self, interaction: discord.Interaction, interval: int):
        try:
            self.usnotifier.set_interval(interval)
            await interaction.response.send_message(f"Interval set to {interval} seconds")
        except ValueError as e:
            await interaction.response.send_message(f"Set interval failed with error {e}")


    async def send_notification(self, session_infos: List[SessionInfo]):
        if self.alert_channel_id == None:
            return

        if len(session_infos) == 0:
            logging.info("Empty session info")
            return

        grouped_sessions = self.group_by_course(session_infos)

        for sport_title, channel_ids in self.alert_channel_id.items():
            sessions = grouped_sessions.get(sport_title, [])

            logging.info(f"For {sport_title}: {sessions}")

            if len(sessions) == 0:
                return
            
            formatted_alert = self.format_session_infos(sessions)

            logging.info(f"Sending {formatted_alert}")

            for channel_id in channel_ids:
                channel = self.get_channel(channel_id)

                if channel is None:
                    channel = await self.fetch_channel(channel_id)

                await channel.send(formatted_alert)

    def group_by_course(self, session_infos: List[SessionInfo]) -> Dict[str, List[SessionInfo]]:
        grouped_sessions = dict()
        for info in session_infos:
            grouped_sessions[info.sport_title] = grouped_sessions.get(info.sport_title, []) + [info]

        return grouped_sessions

    def format_session_infos(self, session_infos: List[SessionInfo]) -> str:
        formatted_string = ""
        for info in session_infos:
            formatted_string += f"@everyone 🏐 {info.sport_title} on 📅 {info.day} {info.datetime} at 🕙 {info.hour}: {info.num_spots} available in 🏫 {info.room} !!\n"
        
        return formatted_string
    
