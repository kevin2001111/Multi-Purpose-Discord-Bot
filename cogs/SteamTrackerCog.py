import json
import pytz
import os
import discord
import requests
from dotenv import load_dotenv 
from datetime import datetime
from discord.ext import commands, tasks

load_dotenv()
TRACK_LIST_PRICE_CHECK_TIME = [(2, 0)]

class SteamTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = requests.Session()
        self.base_url = "https://store.steampowered.com/api"
        self.tracked_file = r'C:\Users\kevintsai\Desktop\DCbot\cogs\tracked_games.json'
        self.load_tracked_games()

    def load_tracked_games(self):
        """載入追蹤清單"""
        if os.path.exists(self.tracked_file):
            with open(self.tracked_file, 'r', encoding='utf-8') as f:
                self.tracked_games = json.load(f)
        else:
            self.tracked_games = {}

    def save_tracked_games(self):
        """儲存追蹤清單"""
        with open(self.tracked_file, 'w', encoding='utf-8') as f:
            json.dump(self.tracked_games, f, ensure_ascii=False, indent=2)

    def search_game(self, query):
        """搜尋 Steam 遊戲"""
        url = f"https://store.steampowered.com/api/storesearch"
        params = {
            'term': query,
            'l': 'traditional_chinese',
            'cc': 'tw'
        }
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

    def current_price(self, app_id):
        """獲取當前遊戲價格"""
        details = self.get_game_details(app_id)
        if details and str(app_id) in details and details[str(app_id)]['success']:
            game_info = details[str(app_id)]['data']
            return game_info['price_overview']['final'] if 'price_overview' in game_info else 'N/A'
        return 'N/A'

    def get_game_details(self, app_id):
        """獲取遊戲詳細資訊"""
        url = f"{self.base_url}/appdetails"
        params = {
            'appids': app_id,
            'cc': 'tw',
            'l': 'traditional_chinese'
        }
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

    @commands.command(name='search')
    async def search_steam(self, ctx, *, query):
        """搜尋 Steam 遊戲"""
        await ctx.send(f"正在搜尋 {query} 的遊戲...")
        results = self.search_game(query)
        if results and 'items' in results:
            embed = discord.Embed(
                title=f"搜尋結果: {query}",
                description="",
                color=discord.Color.blue()
            )
            for item in results['items'][:5]:  # 顯示前5個結果
                embed.add_field(
                    name=item['name'],
                    value=f"[商店頁面](https://store.steampowered.com/app/{item['id']})",
                    inline=False
                )
            await ctx.send(embed=embed)
        else:
            await ctx.send("未找到任何遊戲!")

    @commands.command(name='track')
    async def track_game(self, ctx, app_id: int, alert_price: str):
        """追蹤 Steam 遊戲"""
        details = self.get_game_details(app_id)
        if details and str(app_id) in details and details[str(app_id)]['success']:
            game_info = details[str(app_id)]['data']
            self.tracked_games[app_id] = {
                'name': game_info['name'],
                'alert_price': alert_price,
                'header_image': game_info['header_image']
            }
            self.save_tracked_games()
            await ctx.send(f"已開始追蹤遊戲: {game_info['name']}")
        else:
            await ctx.send("無法找到該遊戲或獲取遊戲詳細資訊失敗!")

    @commands.command(name='untrack')
    async def untrack_game(self, ctx, app_id: int, game_name: str):
        """取消追蹤 Steam 遊戲"""
        if app_id in self.tracked_games:
            del self.tracked_games[(app_id, game_name)]
            self.save_tracked_games()
            await ctx.send(f"已取消追蹤遊戲: {game_name}")
        else:
            await ctx.send("該遊戲不在追蹤清單中!")

    @commands.command(name='list')
    async def tracked_games(self, ctx):
        """顯示追蹤的遊戲清單"""
        if not self.tracked_games:
            await ctx.send("目前沒有追蹤任何遊戲!")
            return

        embed = discord.Embed(
            title="追蹤的遊戲清單",
            description="",
            color=discord.Color.green()
        )
        for app_id, game_info in self.tracked_games.items():
            embed.add_field(
                name=game_info['name'],
                value=f"遊戲ID: {app_id}\n\
                        目標價格: NT${game_info['alert_price']}\n\
                        當前價格: NT${self.current_price(app_id)//100 if self.current_price(app_id) != 'N/A' else 'N/A'}",
                inline=False
            )
            if 'header_image' in game_info:
                embed.set_image(url=game_info['header_image'])

        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def price_check(self):
        now = datetime.now(pytz.timezone('Asia/Taipei'))
        current_time = (now.hour, now.minute)   

        if current_time in TRACK_LIST_PRICE_CHECK_TIME:
            channel = self.bot.get_channel(int(os.getenv('STEAM_CHANNEL_ID')))
            role = discord.utils.get(channel.guild.roles, id=int(os.getenv('STEAM_ROLE_ID')))
            if channel and role:
                try:
                    for app_id, game_info in self.tracked_games.items():
                        current_price = self.current_price(app_id)
                        if current_price != 'N/A' and int(current_price) <= int(game_info['alert_price']):
                            embed = discord.Embed(
                                title=f"{game_info['name']} 已達到目標價格!",
                                description=f"當前價格: NT${current_price//100}",
                                color=discord.Color.red()
                            )
                            embed.set_image(url=game_info['header_image'])
                            await channel.send(f"{role.mention}", embed=embed)
                except Exception as e:
                    print(f"Error sending price alert: {e}")

    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

def setup(bot):
    bot.add_cog(SteamTrackerCog(bot))