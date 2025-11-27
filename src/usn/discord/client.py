# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import Intents
from typing import Any, List
import logging
import asyncio

from ..api.notifier import USNotifier
from ..api.status import SessionInfo


import discord
from discord.ext import commands

class USNDiscordBot(commands.Bot):
    def __init__(self, intents: Intents):
        super().__init__(command_prefix="!", intents=intents)
        
        # Mutable state
        self.usnotifier = USNotifier(interval=300, callback=self.send_notification)

        # Setup slash commands
        self.tree.command(name="watch", description="Set a watched course (give the URL)")(self.watch_url)
        self.tree.command(name="setchannel", description="Set the channel to messages")(self.set_channel)
        self.tree.command(name="setinterval", description="Set an interval")(self.set_interval)
        self.tree.command(name="launch", description="Launch !")(self.launch)
        self.tree.command(name="stop", description="Stop notifications")(self.stop)

        self.alert_channel_id = None

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_resumed(self):
        logging.info("Bot reconnected — ensuring notifier is running.")

        # If your notifier has a flag to check its state
        if not self.usnotifier.is_running and self.usnotifier.should_run:
            self.loop.create_task(self.usnotifier.start())

    async def watch_url(self, interaction: discord.Interaction, course_url: str):
        self.usnotifier.add_watch_url(course_url)
        await interaction.response.send_message(f"Watching course {course_url}")

    async def set_channel(self, interaction: discord.Interaction):
        self.alert_channel_id = interaction.channel.id
        await interaction.response.send_message(f"Channel set for alerts: {self.alert_channel_id}")

    async def set_interval(self, interaction: discord.Interaction, interval: int):
        try:
            self.usnotifier.set_interval(interval)
            await interaction.response.send_message(f"Interval set to {interval} seconds")
        except ValueError as e:
            await interaction.response.send_message(f"Set interval failed with error {e}")

    async def launch(self, interaction: discord.Interaction):
        self.loop.create_task(self.usnotifier.start())
        await interaction.response.send_message(f"Launched application!")

    async def stop(self, interaction: discord.Interaction):
        self.usnotifier.stop()
        await interaction.response.send_message(f"Stopped application!")

    async def send_notification(self, session_infos: List[SessionInfo]):
        if self.alert_channel_id == None:
            return

        if len(session_infos) == 0:
            logging.info("Empty session info")
            return

        channel = self.get_channel(self.alert_channel_id)
        if channel is None:
            channel = await self.fetch_channel(self.alert_channel_id)

        formatted_alert = self.format_session_infos(session_infos)

        await channel.send(formatted_alert)

    def format_session_infos(self, session_infos: List[SessionInfo]) -> str:
        formatted_string = ""
        for info in session_infos:
            formatted_string += f"@everyone 🏐 {info.sport_title} on 📅 {info.day} {info.datetime} at 🕙 {info.hour}: {info.num_spots} available !!\n"
        
        return formatted_string
    
