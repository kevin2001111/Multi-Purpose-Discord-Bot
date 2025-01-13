import discord
import os
import asyncio
import pytz
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

# Basic bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='$$', intents=intents)
bot.timezone = pytz.timezone('Asia/Taipei')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content == '$$':
        embed = discord.Embed(
            title="可用指令列表",
            description="以下是所有可用的指令：",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎵 音樂指令",
            value="""
            `$$join` - 加入語音頻道
            `$$play <歌曲名稱或URL>` - 播放音樂
            `$$playlist <List's URL>` - 播放清單音樂
            `$$pause` - 暫停播放
            `$$resume` - 繼續播放
            `$$skip` - 跳過當前歌曲
            `$$queue` - 查看播放隊列
            `$$clear` - 清空播放隊列
            `$$leave` - 離開語音頻道
            """,
            inline=False
        )

        embed.add_field(
            name="<:Steam:1327469891782967347> Steam 指令",
            value="""
            `$$search <遊戲名稱>` - 搜尋 Steam 遊戲
            `$$track <遊戲ID> <期望價格>` - 追蹤遊戲價格
            `$$untrack <遊戲ID>` - 取消追蹤遊戲
            `$$list` - 列出追蹤清單
            """,
            inline=False
        )

        embed.add_field(
            name="<:emojigg_R6:1327556770788282451> R6 指令",
            value="""
            `$$r6 <玩家名稱>` - 查詢該 R6 玩家數據
            """,
            inline=False
        )
         
        await message.channel.send(embed=embed)
        return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'{bot.user} 已經上線!')
    print(f'目前在 {len(bot.guilds)} 個伺服器中')
    
    activity = discord.Activity(
        type=discord.ActivityType.listening, 
        name="$$ | $$help"
    )
    await bot.change_presence(activity=activity)

# 載入指令程式檔案
@bot.command()
@commands.is_owner() 
async def load(ctx, extension):
    try:
        bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Loaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error loading {extension}: {str(e)}")

# 卸載指令檔案
@bot.command()
@commands.is_owner() 
async def unload(ctx, extension):
    try:
        bot.unload_extension(f"cogs.{extension}")
        await ctx.send(f"Unloaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error unloading {extension}: {str(e)}")


# 重新載入程式檔案
@bot.command()
@commands.is_owner() 
async def reload(ctx, extension):
    try:
        bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"Reloaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error reloading {extension}: {str(e)}")


# 一開始bot開機需載入全部程式檔案
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "r6.py":
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load {filename[:-3]}: {str(e)}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())