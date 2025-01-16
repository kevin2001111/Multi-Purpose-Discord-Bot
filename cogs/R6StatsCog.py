import discord
from discord.ext import commands
from .r6 import track_main  # Adjusted import statement

class R6StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='r6')
    async def r6(self, ctx, username):
        """Rainbow Six Siege 統計"""
        await ctx.send(f"正在獲取 {username} 的統計數據...")
        stats, pic = track_main(username)

        platform = stats.get('platform', 'N/A')
        if platform == 'ubi':
            platform_str = "<:Ubisoft:1327557343973478440> 平台: Ubisoft\n"
        elif platform == 'psn':
            platform_str = "<:PlaystationWhite:1327555698061738068> 平台: PlayStation\n"
        else:
            platform_str = "<:Xbox:1327557470884728853> 平台: Xbox\n"

        embed = discord.Embed(
            title=f"{username} 排名數據 (Y9S4)",
            description="",
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"📝 用戶名: {username}",
            value="",
            inline=False
        )

        embed.add_field(
            name=platform_str,
            value="",
            inline=False
        )

        embed.add_field(
            name=f"⭐ 等級: {stats.get('level', 'N/A')}",
            value="",
            inline=False
        )

        current_rank = stats.get('rank', 'N/A').split(" ")[0]
        if current_rank == 'COPPER':
            rank_str = f"<:copper:1327562943721902090> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'BRONZE':
            rank_str = f"<:bronze:1327562905423446068> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'SILVER':
            rank_str = f"<:Silver:1327563130246529094> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'GOLD':
            rank_str = f"<:gold:1327562853250764832> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'PLATINUM':
            rank_str = f"<:rainbowsixsigeplatinum:1327562985924988928> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'EMERALD':
            rank_str = f"<:emerald:1327562807969054791> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'DIAMOND':
            rank_str = f"<:RainbowSixSiegeDiamond:1327563043210530877> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        elif current_rank == 'CHAMPION':
            rank_str = f"<:r6champ:1327468512603668622> Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        else:
            rank_str = f"Rank {stats.get('rank', 'N/A')} | RP {stats.get('points', 'N/A')} | Best RP {stats.get('best_points', 'N/A')}"
        
        embed.add_field(
            name=rank_str,
            value="",
            inline=False
        )

        embed.set_thumbnail(url=pic)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

async def setup(bot):
    await bot.add_cog(R6StatsCog(bot))