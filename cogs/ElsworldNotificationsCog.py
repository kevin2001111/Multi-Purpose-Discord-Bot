import discord
import pytz
import os
from datetime import datetime
from discord.ext import commands, tasks

NOTIFICATION_TIMES_163 = [
    (7, 0), (11, 0), (15, 0), 
    (19, 0), (23, 0), (3, 0), 
]
NOTIFICATION_TIMES_194 = [
    (9, 0), (13, 0), (17, 0), 
    (21, 0), (1, 0), (5, 0),
]

_163_IMAGE_PATH = r"C:\Users\kevintsai\Desktop\DCbot\cogs\163.png"
_194_IMAGE_PATH = r"C:\Users\kevintsai\Desktop\DCbot\cogs\194.png"

class ElsworldNotificationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._163_notification.start()
        self._194_notification.start()

    @tasks.loop(minutes=1)
    async def _163_notification(self):
        now = datetime.now(pytz.timezone('Asia/Taipei'))
        current_time = (now.hour, now.minute)
        
        if current_time in NOTIFICATION_TIMES_163:
            channel = self.bot.get_channel(1326555585352827021)
            role = discord.utils.get(channel.guild.roles, id=1326555643531886684)
            
            if channel and role:
                try:
                    # Create embed with dungeon information
                    embed = discord.Embed(
                        title="163-普雷加斯的迷宮",
                        description=f"{current_time[0]}:{current_time[1]}0囉！該打163了！",
                        color=discord.Color.gold()
                    )
                    
                    # Add image if it exists
                    if os.path.exists(_163_IMAGE_PATH):
                        file = discord.File(_163_IMAGE_PATH, filename="163.png")
                        embed.set_image(url="attachment://163.png")
                        await channel.send(f"{role.mention}", embed=embed, file=file)
                    else:
                        await channel.send(f"{role.mention}", embed=embed)
                        
                except Exception as e:
                    print(f"Error sending dungeon notification: {e}")

    @tasks.loop(minutes=1)
    async def _194_notification(self):
        now = datetime.now(pytz.timezone('Asia/Taipei'))
        current_time = (now.hour, now.minute)
        
        if current_time in NOTIFICATION_TIMES_194:
            channel = self.bot.get_channel(1326555585352827021)
            role = discord.utils.get(channel.guild.roles, id=1326555643531886684)
            
            if channel and role:
                try:
                    # Create embed with dungeon information
                    embed = discord.Embed(
                        title="194-普雷加斯的迷宮",
                        description=f"{current_time[0]}:{current_time[1]}0囉！該打194了！",
                        color=discord.Color.gold()
                    )
                    
                    # Add image if it exists
                    if os.path.exists(_194_IMAGE_PATH):
                        file = discord.File(_194_IMAGE_PATH, filename="194.png")
                        embed.set_image(url="attachment://194.png")
                        await channel.send(f"{role.mention}", embed=embed, file=file)
                    else:
                        await channel.send(f"{role.mention}", embed=embed)
                        
                except Exception as e:
                    print(f"Error sending dungeon notification: {e}")

    @_163_notification.before_loop
    @_194_notification.before_loop
    async def before_notifications(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

def setup(bot: commands.Bot):
    bot.add_cog(ElsworldNotificationsCog(bot))