import json
import pytz
import os
import discord
import requests
import aiohttp
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
        details_tw = self.get_game_details_tw(app_id)
        details_us = self.get_game_details_us(app_id)
        game_info_tw = {}
        game_info_us = {}
        if details_tw and str(app_id) in details_tw and details_tw[str(app_id)]['success']:
            game_info_tw = details_tw[str(app_id)]['data']
        if details_us and str(app_id) in details_us and details_us[str(app_id)]['success']:
            game_info_us = details_us[str(app_id)]['data']

        if 'price_overview' in game_info_tw and 'price_overview' in game_info_us:
            return (game_info_tw['price_overview']['final'], game_info_us['price_overview']['final'])
        elif 'price_overview' in game_info_tw:
            return (game_info_tw['price_overview']['final'], 'N/A')
        elif 'price_overview' in game_info_us:
            return ('N/A', game_info_us['price_overview']['final'])
        else:
            return ('N/A', 'N/A')

    def get_game_details_tw(self, app_id):
        """獲取遊戲詳細資訊"""
        url = f"{self.base_url}/appdetails"
        params = {
            'appids': app_id,
            'cc': 'tw',
            'l': 'traditional_chinese'
        }
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None
    
    def get_game_details_us(self, app_id):
        """獲取遊戲詳細資訊"""
        url = f"{self.base_url}/appdetails"
        params = {
            'appids': app_id,
            'cc': 'us',
            'l': 'english'
        }
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

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
                        史低價格: USD$ {game_info['historical_price']}\n\
                        當前價格: NT$ {self.current_price(app_id)[0]//100 if self.current_price(app_id)[0] != 'N/A' else 'N/A'} / USD$ {self.current_price(app_id)[1]/100 if self.current_price(app_id)[1] != 'N/A' else 'N/A'}",
                inline=False
            )
        await ctx.send(embed=embed)
    
    @commands.command(name='connect')
    async def connect(self, ctx, steam_id: str):
        user_id = str(ctx.author.id)
        self.load_dcid_connect_steamid_json()
        self.dcid_connect_steamid[user_id] = steam_id
        self.save_dcid_connect_steamid_json()
        await ctx.send(f"已順利連結")

    @commands.command(name='create')
    async def create(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in self.dcid_connect_steamid:
            await ctx.send("請先連結 Steam ID!")
            return
        
        if user_id not in self.tracked_games:
            self.tracked_games[user_id] = {}
        
        steam_id = self.dcid_connect_steamid[user_id]
        wishlist_url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?access_token={os.getenv('STEAM_ACCESS_TOKEN')}&steamid={str(steam_id)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(wishlist_url) as wishlist_response:
                if wishlist_response.status == 200:
                    data = await wishlist_response.json()
                    total_items = len(data['response']['items'])
                    message = await ctx.send(f"正在更新 Steam 願望清單... 0/{total_items}")
                        
                    for index, item in enumerate(data['response']['items'], start=1):
                        if str(item['appid']) in self.tracked_games[user_id]:
                            await message.edit(content=f"正在更新 Steam 願望清單... {index}/{total_items}")
                            continue
                        isthereanydeal_url = f"https://api.isthereanydeal.com/games/lookup/v1?key={os.getenv('ISTHEREANYDEAL_API_KEY')}&appid={str(item['appid'])}"
                        details = self.get_game_details_tw(item['appid'])
                        if details and str(item['appid']) in details and details[str(item['appid'])]['success']:
                            game_info = details[str(item['appid'])]['data']
                            
                            # 獲取 IsThereAnyDeal 資訊
                            async with session.get(isthereanydeal_url) as itad_response:
                                if itad_response.status == 200:
                                    itad_data = await itad_response.json()
                                    game_info['isthereanydeal_id'] = itad_data['game']['id']
                                    
                                    # 獲取歷史最低價格
                                    price_url = f"https://api.isthereanydeal.com/games/storelow/v2?shops=61&key={os.getenv('ISTHEREANYDEAL_API_KEY')}"
                                    body = [game_info['isthereanydeal_id']]
                                    async with session.post(price_url, json=body) as price_response:
                                        if price_response.status == 200:
                                            price_data = await price_response.json()
                                            if price_data and len(price_data) > 0:
                                                game_info['historical_price'] = price_data[0]['lows'][0]['price']['amount']
                                                game_info['currency'] = price_data[0]['lows'][0]['price']['currency']
                                            else:
                                                await ctx.send(f"無法取得 {game_info['name']} 的歷史價格資訊。")
                                        else:
                                            await ctx.send(f"無法取得 {game_info['name']} 的歷史價格資訊。")
                            
                            self.tracked_games[user_id][item['appid']] = {
                                'name': game_info['name'],
                                'header_image': game_info['header_image'],
                                'date_added': self.convert_unix_timestamp(item['date_added']),
                                'isthereanydeal_id': game_info.get('isthereanydeal_id'),
                                'historical_price': game_info.get('historical_price'),
                                'currency': game_info.get('currency')
                            }
                            
                        await message.edit(content=f"正在更新 Steam 願望清單... {index}/{total_items}")
                    self.save_tracked_games()
                    await ctx.send("已更新 Steam 願望清單！")
                else:
                    await ctx.send("無法從 Steam API 取得願望清單。")

    @tasks.loop(hours=168) 
    async def price_check(self):
        now = datetime.now(pytz.timezone('Asia/Taipei'))
        current_time = (now.hour, now.minute)   

        if current_time in TRACK_LIST_PRICE_CHECK_TIME:
            self.load_dcid_connect_steamid_json()
            for user_id in self.dcid_connect_steamid.keys():
                role = discord.utils.get(self.bot.guilds[1].members, id=int(user_id))
                if role:
                    try:
                        for app_id, game_info in self.tracked_games[user_id].items():
                            current_price = self.current_price(app_id)
                            if current_price[1] == 'N/A' or 'historical_price' not in game_info or float(current_price[1]/100) > float(game_info['historical_price']):
                                continue
                            else:
                                embed = discord.Embed(
                                    title=f"{game_info['name']} 已達到史低！",
                                    description=f"當前價格: NT$ {current_price[0]//100}",
                                    color=discord.Color.red()
                                )
                                embed.set_image(url=game_info['header_image'])
                                await role.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending price alert: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        self.price_check.start()
        print(f"{self.__class__.__name__} is ready!")

async def setup(bot):
    await bot.add_cog(SteamTrackerCog(bot))