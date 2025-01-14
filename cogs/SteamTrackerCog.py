import json
import pytz
import os
import discord
import requests
import aiohttp
from typing import Dict
from steam_web_api import Steam
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
        self.tracked_file = r'steam\tracked_games.json'
        self.connect_file = r'steam\dcid_connect_steamid.json'
        self.ensure_files_exist()
        self.load_tracked_games()
        self.load_dcid_connect_steamid_json()

    def ensure_files_exist(self):
        """確保所需的文件存在"""
        if not os.path.exists('steam'):
            os.makedirs('steam')
        if not os.path.exists(self.tracked_file):
            with open(self.tracked_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        if not os.path.exists(self.connect_file):
            with open(self.connect_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def load_dcid_connect_steamid_json(self):
        """載入追蹤清單"""
        with open(self.connect_file, 'r', encoding='utf-8') as f:
            self.dcid_connect_steamid = json.load(f)
    
    def save_dcid_connect_steamid_json(self):
        """儲存追蹤清單"""
        with open(self.connect_file, 'w', encoding='utf-8') as f:
            json.dump(self.dcid_connect_steamid, f, ensure_ascii=False, indent=2)

    def load_tracked_games(self):
        """載入追蹤清單"""
        with open(self.tracked_file, 'r', encoding='utf-8') as f:
            self.tracked_games = json.load(f)

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

    def get_game_name(self, app_id: int) -> str:
        """根據 app_id 獲取遊戲名稱"""
        details = self.get_game_details(app_id)
        if details and str(app_id) in details and details[str(app_id)]['success']:
            game_info = details[str(app_id)]['data']
            return game_info['name']
        return "Unknown Game"

    def convert_unix_timestamp(self, timestamp: int) -> str:
        """將 Unix 時間戳轉換為可讀格式"""
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    
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
                    value=f"ID: {item['id']}\n\
                            [商店頁面](https://store.steampowered.com/app/{item['id']})",
                    inline=False
                )
            await ctx.send(embed=embed)
        else:
            await ctx.send("未找到任何遊戲!")

    @commands.command(name='track')
    async def track_game(self, ctx, app_id: int, alert_price: str):
        """追蹤 Steam 遊戲"""
        user_id = str(ctx.author.id)
        if user_id in self.tracked_games and app_id in self.tracked_games[user_id]:
            await ctx.send(f"該遊戲已在追蹤清單中: {self.tracked_games[user_id][app_id]['name']}")
            return

        details = self.get_game_details(app_id)
        if details and str(app_id) in details and details[str(app_id)]['success']:
            game_info = details[str(app_id)]['data']
            if user_id not in self.tracked_games:
                self.tracked_games[user_id] = {}
            self.tracked_games[user_id][app_id] = {
                'name': game_info['name'],
                'alert_price': alert_price,
                'header_image': game_info['header_image']
            }
            self.save_tracked_games()
            await ctx.send(f"已開始追蹤遊戲: {game_info['name']}")
        else:
            await ctx.send("無法找到該遊戲或獲取遊戲詳細資訊失敗!")

    @commands.command(name='untrack')
    async def untrack_game(self, ctx, app_id: str):
        """取消追蹤 Steam 遊戲"""
        user_id = str(ctx.author.id)
        if user_id in self.tracked_games and app_id in self.tracked_games[user_id]:
            game_name = self.tracked_games[user_id][app_id]['name']
            del self.tracked_games[user_id][app_id]
            self.save_tracked_games()
            await ctx.send(f"已取消追蹤遊戲: {game_name}")
        else:
            await ctx.send("該遊戲不在追蹤清單中!")

    @commands.command(name='list')
    async def list(self, ctx):
        """顯示追蹤的遊戲清單"""
        user_id = str(ctx.author.id)
        if user_id not in self.tracked_games or not self.tracked_games[user_id]:
            await ctx.send("目前沒有追蹤任何遊戲!")
            return

        embed = discord.Embed(
            title="追蹤的遊戲清單",
            description="",
            color=discord.Color.green()
        )
        for app_id, game_info in list(self.tracked_games[user_id].items())[:10]:  # 只顯示前10筆
            embed.add_field(
                name=game_info['name'],
                value=f"遊戲ID: {app_id}\n\
                        目標價格: NT$ {game_info['alert_price']}\n\
                        當前價格: NT$ {self.current_price(app_id)//100 if self.current_price(app_id) != 'N/A' else 'N/A'}",
                inline=False
            )
        await ctx.send(embed=embed)
    
    @commands.command(name='update')
    async def update_wishlist(self, ctx):
        """更新 Steam 願望清單"""
        user_id = str(ctx.author.id)
        if user_id not in self.dcid_connect_steamid:
            await ctx.send("請先連結 Steam ID!")
            return
        steam_id = self.dcid_connect_steamid[user_id]
        url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?access_token={os.getenv('STEAM_ACCESS_TOKEN')}&steamid={str(steam_id)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    total_items = len(data['response']['items'])
                    message = await ctx.send(f"正在更新 Steam 願望清單... 0/{total_items}")
                    if user_id not in self.tracked_games:
                        self.tracked_games[user_id] = {}
                    for index, item in enumerate(data['response']['items'], start=1):
                        if str(item['appid']) in self.tracked_games[user_id]:
                            await message.edit(content=f"正在更新 Steam 願望清單... {index}/{total_items}")
                            continue
                        details = self.get_game_details(item['appid'])
                        if details and str(item['appid']) in details and details[str(item['appid'])]['success']:
                            game_info = details[str(item['appid'])]['data']
                            self.tracked_games[user_id][item['appid']] = {
                                'name': game_info['name'],
                                'alert_price': '0',
                                'header_image': game_info['header_image'],
                                'date_added': self.convert_unix_timestamp(item['date_added'])
                            }
                        await message.edit(content=f"正在更新 Steam 願望清單... {index}/{total_items}")
                    self.save_tracked_games()
                else:
                    await ctx.send("Failed to retrieve wishlist from Steam API.")
        await ctx.send("已更新 Steam 願望清單!")

    @commands.command(name='connect')
    async def connect(self, ctx, steam_id: str):
        user_id = str(ctx.author.id)
        self.load_dcid_connect_steamid_json()
        self.dcid_connect_steamid[user_id] = steam_id
        self.save_dcid_connect_steamid_json()
        await ctx.send(f"已順利連結")

    @commands.command(name='buildlist')
    @commands.is_owner() 
    async def buildlist(self, ctx):
        url = f"https://api.steampowered.com/ISteamApps/GetAppList/v2/?access_token={os.getenv('STEAM_ACCESS_TOKEN')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    with open(r'steam\steam_app_list.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    await ctx.send("Successfully retrieved and saved app list from Steam API.")
                else:
                    await ctx.send("Failed to retrieve app list from Steam API.")

    @commands.command(name='rebuildlist')
    @commands.is_owner() 
    async def rebuildlist(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in self.tracked_games:
            await ctx.send("No games to rebuild.")
            return
        for app_id, game_info in self.tracked_games[user_id].items():
            url = f"https://api.isthereanydeal.com/games/lookup/v1?key={os.getenv('ISTHEREANYDEAL_API_KEY')}&appid={app_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        del game_info['alert_price']
                        game_info['isthereanydeal_id'] = data['game']['id']
                    else:
                        await ctx.send("Failed to retrieve app list from Steam API.")
                        break
        self.save_tracked_games()
        print("Rebuilt tracked games list.")

    @commands.command(name='historical')
    @commands.is_owner()
    async def historical_price(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in self.tracked_games:
            await ctx.send("No games to retrieve historical prices.")
            return
        total_games = len(self.tracked_games[user_id])
        message = await ctx.send(f"Retrieving historical prices... 0/{total_games}")
        for index, (app_id, game_info) in enumerate(self.tracked_games[user_id].items(), start=1):
            url = f"https://api.isthereanydeal.com/games/storelow/v2?shops=61&key={os.getenv('ISTHEREANYDEAL_API_KEY')}"
            body = [game_info['isthereanydeal_id']]
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        game_info['historical_price'] = data[0]['lows'][0]['price']['amount']
                        game_info['currency'] = data[0]['lows'][0]['price']['currency']
                    else:
                        await ctx.send(f"Failed to retrieve historical price for {game_info['name']}.")
            await message.edit(content=f"Retrieving historical prices... {index}/{total_games}")
        self.save_tracked_games()
        await ctx.send("Historical prices retrieved and updated.")

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