import json
import os
import discord
import requests
from discord.ext import commands

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
            for item in results['items'][:10]:  # 顯示前10個結果
                embed.add_field(
                    name=item['name'],
                    value=f"[商店頁面](https://store.steampowered.com/app/{item['id']})",
                    inline=False
                )
            await ctx.send(embed=embed)
        else:
            await ctx.send("未找到任何遊戲!")

    @commands.command(name='track')
    async def track_game(self, ctx, app_id: int):
        """追蹤 Steam 遊戲"""
        details = self.get_game_details(app_id)
        if details and str(app_id) in details and details[str(app_id)]['success']:
            game_info = details[str(app_id)]['data']
            self.tracked_games[app_id] = {
                'name': game_info['name'],
                'price': game_info['price_overview']['final'] if 'price_overview' in game_info else '免費'
            }
            self.save_tracked_games()
            await ctx.send(f"已開始追蹤遊戲: {game_info['name']}")
        else:
            await ctx.send("無法找到該遊戲或獲取遊戲詳細資訊失敗!")

    @commands.command(name='untrack')
    async def untrack_game(self, ctx, app_id: int):
        """取消追蹤 Steam 遊戲"""
        if app_id in self.tracked_games:
            game_name = self.tracked_games[app_id]['name']
            del self.tracked_games[app_id]
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
            print(app_id, game_info)
            embed.add_field(
                name=game_info['game_name'],
                value=f"目標價格: {game_info['alert_price']}",
                inline=False
            )
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

def setup(bot):
    bot.add_cog(SteamTrackerCog(bot))