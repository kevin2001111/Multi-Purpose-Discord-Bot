import discord
import os
import asyncio
import pytz
import time
from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()

# Basic bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='$$', intents=intents)
bot.timezone = pytz.timezone('Asia/Taipei')
bot.start_time = time.time()  # Track when the bot started
bot.voice_last_activity = {}  # Track last activity time for each server

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 更新語音頻道活動時間
    if message.guild and message.guild.id in bot.voice_last_activity:
        guild_id = message.guild.id
        voice_client = message.guild.voice_client
        if voice_client and voice_client.is_connected():
            bot.voice_last_activity[guild_id] = time.time()

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
            `$$loop` - 切換循環模式
            `$$leave` - 離開語音頻道
            """,
            inline=False
        )
         
        await message.channel.send(embed=embed)
        return

    elif message.content == "$$help":
        # 建立嵌入式訊息
        embed = discord.Embed(title="機器人指令幫助", description="以下是可用的命令列表", color=0x00ff00)
        
        # 音樂指令
        embed.add_field(name="音樂指令", value="$$play [歌名或URL] - 播放音樂\n$$skip - 跳過當前歌曲\n$$pause - 暫停播放\n$$resume - 繼續播放\n$$stop - 停止播放並清空隊列\n$$queue - 顯示播放隊列\n$$clear - 清空播放隊列\n$$player - 顯示音樂播放器控制面板\n$$loop - 切換循環模式", inline=False)
        
        # 發送嵌入式訊息
        await message.channel.send(embed=embed)

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    """當用戶在語音頻道中的狀態改變時觸發"""
    if member.bot:
        return
        
    if member.guild.id in bot.voice_last_activity:
        # 更新該伺服器的最後活動時間
        bot.voice_last_activity[member.guild.id] = time.time()

@tasks.loop(seconds=60)
async def check_voice_activity():
    """定期檢查語音頻道活動，如果30分鐘內無活動則退出"""
    current_time = time.time()
    timeout_duration = 30 * 60  # 30分鐘超時
    
    for guild in bot.guilds:
        if guild.id in bot.voice_last_activity:
            voice_client = guild.voice_client
            
            # 檢查機器人是否在語音頻道中
            if voice_client and voice_client.is_connected():
                last_activity = bot.voice_last_activity[guild.id]
                
                # 如果超過30分鐘無活動，退出頻道
                if current_time - last_activity > timeout_duration:
                    await voice_client.disconnect()
                    print(f"已自動退出 {guild.name} 的語音頻道 (30分鐘無活動)")
                    del bot.voice_last_activity[guild.id]

@check_voice_activity.before_loop
async def before_check_voice_activity():
    """等待機器人啟動完成再開始檢查"""
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f'{bot.user} 已經上線!')
    print(f'目前在 {len(bot.guilds)} 個伺服器中')
    
    activity = discord.Activity(
        type=discord.ActivityType.listening, 
        name="$$ | $$help"
    )
    await bot.change_presence(activity=activity)
    
    # 啟動自動檢查語音活動的任務
    check_voice_activity.start()

# 載入指令程式檔案
@bot.command()
@commands.is_owner() 
async def load(ctx, extension):
    try:
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Loaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error loading {extension}: {str(e)}")

# 卸載指令檔案
@bot.command()
@commands.is_owner() 
async def unload(ctx, extension):
    try:
        await bot.unload_extension(f"cogs.{extension}")
        await ctx.send(f"Unloaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error unloading {extension}: {str(e)}")


# 重新載入程式檔案
@bot.command()
@commands.is_owner() 
async def reload(ctx, extension):
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"Reloaded {extension} done.")
    except Exception as e:
        await ctx.send(f"Error reloading {extension}: {str(e)}")

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutdown...")
    check_voice_activity.cancel()  # 取消定時任務
    await bot.close()

# 更新音樂相關命令的處理器，記錄活動時間
@bot.listen()
async def on_command(ctx):
    """當命令被調用時更新語音活動時間"""
    # 只更新語音相關命令
    music_commands = ['join', 'play', 'playlist', 'pause', 'resume', 
                      'skip', 'queue', 'clear', 'loop', 'leave', 'player']
    
    if ctx.command.name in music_commands and ctx.guild:
        bot.voice_last_activity[ctx.guild.id] = time.time()

# 一開始bot開機需載入全部程式檔案
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                # 嘗試加載擴展，顯示更詳細的錯誤信息
                extension_name = f"cogs.{filename[:-3]}"
                await bot.load_extension(extension_name)
                print(f"Loaded {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load {filename[:-3]}: {str(e)}")
                # 列印更多詳細信息以幫助調試
                import traceback
                traceback.print_exc()

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())