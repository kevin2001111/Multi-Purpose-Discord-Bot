import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
from collections import deque
import random
import time
from datetime import datetime, timedelta
from discord.ui import View
import re
from itertools import islice
import os

class MusicControlView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx
        self.message = None
    
    async def interaction_check(self, interaction):
        # 只有發起命令的使用者可以使用按鈕
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("只有發起指令的人可以控制播放器", ephemeral=True)
            return False
        return True
    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.gray)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.cog.voice_clients.get(self.ctx.guild.id):
            vc = self.cog.voice_clients[self.ctx.guild.id]
            if vc.is_paused():
                await self.cog.resume(self.ctx)
            else:
                await self.cog.pause(self.ctx)
            await self.update_player()

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.previous_song(self.ctx)
        await self.update_player()
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.skip(self.ctx)
        await self.update_player()
    
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.gray)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.stop(self.ctx)
        await self.update_player()
    
    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.gray)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.toggle_loop(self.ctx)
        await self.update_player()
    
    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """更新進度條按鈕"""
        await interaction.response.defer()
        await self.update_player()
        # 發送一個短暫的提示訊息
        await interaction.followup.send("進度已更新！", ephemeral=True, delete_after=2)
    
    async def update_player(self):
        if not self.message:
            return
        
        guild_id = self.ctx.guild.id
        embed = discord.Embed(title="🎵 音樂播放器", color=discord.Color.purple())
        
        # 檢查機器人是否在語音頻道中
        if guild_id not in self.cog.voice_clients or not self.cog.voice_clients.get(guild_id):
            embed.description = "目前沒有播放任何歌曲"
            await self.message.edit(embed=embed)
            return
        
        # 檢查是否有當前播放的歌曲
        current = self.cog.current.get(guild_id)
        if not current:
            # 嘗試檢查語音客戶端是否仍在播放
            vc = self.cog.voice_clients.get(guild_id)
            if vc and (vc.is_playing() or vc.is_paused()):
                # 正在播放但current為空，嘗試從隊列獲取信息
                embed.description = "正在播放音樂，但無法獲取歌曲信息。"
                await self.message.edit(embed=embed)
                print(f"警告: {guild_id} 正在播放但無法獲取歌曲信息")
                return
            else:
                # 真的沒有播放任何歌曲
                embed.description = "目前沒有播放任何歌曲"
                await self.message.edit(embed=embed)
                return
        
        # 播放狀態
        vc = self.cog.voice_clients.get(guild_id)
        if not vc:
            embed.description = "機器人不在語音頻道中"
            await self.message.edit(embed=embed)
            return
        
        status = "▶️"
        
        # 循環狀態
        loop_status = "🔁 循環模式: 開啟" if self.cog.loop_mode.get(guild_id, False) else "🔁 循環模式: 關閉"
        
        # 進度條
        progress_info = self.cog.get_progress_info(guild_id)
        if progress_info:
            current_time, duration, percentage = progress_info
            progress_bar = self.cog.create_progress_bar(percentage)
        else:
            current_time = "00:00"
            duration = "00:00"
            progress_bar = "`──────────────────────`"
        
        # 當前歌曲資訊
        title = current.get('title', '未知歌曲')
        url = current.get('webpage_url', '')
        
        embed.description = f"**正在播放:** [{title}]({url})\n\n{loop_status}\n\n{status}  {current_time}  {progress_bar}  {duration}"
        
        # 如果有縮圖
        if 'thumbnail' in current and current['thumbnail']:
            embed.set_thumbnail(url=current['thumbnail'])
        
        # 展示隊列中的下一首歌曲
        queue = self.cog.queues.get(guild_id, [])
        if queue and len(queue) > 0:
            next_songs = list(islice(queue, 0, 3))
            queue_text = "\n".join([f"{i+1}. {song.get('title', '未知歌曲')}" for i, song in enumerate(next_songs)])
            if len(queue) > 3:
                queue_text += f"\n... 還有 {len(queue) - 3} 首歌"
            embed.add_field(name="播放隊列", value=queue_text, inline=False)
        
        await self.message.edit(embed=embed)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.queues = {}
        self.current = {}
        self.start_times = {}
        self.durations = {}
        self.loop_mode = {}  # 新增循環模式
        self.player_contexts = {}  # 儲存控制面板上下文
        self.control_messages = {}  # 儲存控制面板訊息
        
        # 設置ffmpeg路徑 - 優先檢查特定路徑，然後嘗試系統環境變數中的ffmpeg
        self.ffmpeg_path = None
        # 嘗試幾個常見的ffmpeg路徑
        possible_paths = [
            "C:\\Users\\Kevin\\Downloads\\ffmpeg-2025-01-13-git-851a84650e-full_build\\bin\\ffmpeg.exe",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "ffmpeg"
        ]
        for path in possible_paths:
            import shutil
            if path == "ffmpeg" or os.path.exists(path):
                if path == "ffmpeg":
                    ffmpeg_path = shutil.which("ffmpeg")
                    if ffmpeg_path:
                        self.ffmpeg_path = ffmpeg_path
                        break
                else:
                    self.ffmpeg_path = path
                    break
        
        print(f"使用的ffmpeg路徑: {self.ffmpeg_path}")
        
        # YT-DLP 配置
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'extract_flat': 'in_playlist',
        }
        
        # 如果找到ffmpeg，則設置ffmpeg路徑
        if self.ffmpeg_path:
            self.ytdl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
            
        # 註冊按鈕處理函數
        self.bot.add_listener(self.button_callback, "on_interaction")
    
    async def button_callback(self, interaction):
        """處理按鈕交互"""
        if not interaction.data or "custom_id" not in interaction.data:
            return
            
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "playpause":
            await self.handle_play_pause(interaction)
        elif custom_id == "stop":
            await self.handle_stop(interaction)
        elif custom_id == "next":
            await self.handle_next(interaction)
        elif custom_id == "previous":
            await self.handle_previous(interaction)
        elif custom_id == "loop":
            await self.handle_loop(interaction)
    
    async def handle_play_pause(self, interaction):
        """處理播放/暫停按鈕"""
        if not self.ctx or not self.ctx.voice_client:
            await interaction.response.send_message("目前沒有播放歌曲！", ephemeral=True)
            return
            
        if self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
            await interaction.response.send_message("▶️ 已繼續播放", ephemeral=True)
        elif self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            await interaction.response.send_message("⏸️ 已暫停播放", ephemeral=True)
        else:
            await interaction.response.send_message("沒有歌曲正在播放", ephemeral=True)
            
        # 更新控制面板
        await self.update_player()
    
    async def handle_stop(self, interaction):
        """處理停止按鈕"""
        if not self.ctx or not self.ctx.voice_client:
            await interaction.response.send_message("目前沒有播放歌曲！", ephemeral=True)
            return
            
        self.ctx.voice_client.stop()
        await interaction.response.send_message("⏹️ 已停止播放並清空隊列", ephemeral=True)
        
        # 更新控制面板
        await self.update_player()
    
    async def handle_next(self, interaction):
        """處理下一首按鈕"""
        if not self.ctx or not self.ctx.voice_client or not self.ctx.voice_client.is_playing():
            await interaction.response.send_message("目前沒有播放歌曲！", ephemeral=True)
            return
            
        self.ctx.voice_client.stop()  # 停止當前歌曲，會自動播放下一首
        await interaction.response.send_message("⏩ 已跳到下一首", ephemeral=True)
    
    async def handle_previous(self, interaction):
        """處理上一首按鈕"""
        # 因為我們沒有保存播放歷史，所以這個功能比較有限
        # 簡單實現：如果有當前歌曲，重新開始播放
        if not self.ctx or not self.ctx.voice_client or not self.current.get(self.ctx.guild.id):
            await interaction.response.send_message("目前沒有播放歌曲！", ephemeral=True)
            return
        
        # 停止當前歌曲
        self.ctx.voice_client.stop()
        
        # 將當前歌曲重新加入隊列最前面
        if self.current.get(self.ctx.guild.id):
            temp_song = self.current[self.ctx.guild.id]
            if self.ctx.guild.id not in self.queues:
                self.queues[self.ctx.guild.id] = []
            self.queues[self.ctx.guild.id].appendleft(temp_song)
            await self.play_next(self.ctx.guild.id)
            await interaction.response.send_message("⏮️ 重新播放當前歌曲", ephemeral=True)
        else:
            await interaction.response.send_message("無法返回上一首歌曲", ephemeral=True)
    
    async def handle_loop(self, interaction):
        """處理循環模式按鈕"""
        await self.toggle_loop(self.ctx)
    
    async def update_player(self, interaction=None):
        """更新播放器控制面板"""
        if not self.ctx or not self.control_messages.get(self.ctx.guild.id):
            return
            
        try:
            view = MusicControlView(self, self.ctx)
            view.message = self.control_messages[self.ctx.guild.id]
            await view.update_player()
        except Exception as e:
            print(f"更新播放器錯誤: {e}")
    
    async def create_player_embed(self):
        """創建播放器嵌入消息"""
        embed = discord.Embed(
            title="🎵 音樂播放器",
            color=discord.Color.blue()
        )
        
        if not self.ctx or not hasattr(self.ctx, 'guild') or not self.current.get(self.ctx.guild.id):
            embed.description = "目前沒有播放歌曲"
            return embed
            
        embed.description = f"**正在播放:** {self.current[self.ctx.guild.id]['title']}"
        
        # 計算進度
        elapsed_time = int(time.time() - self.start_times.get(self.ctx.guild.id, 0))
        elapsed_str = str(timedelta(seconds=elapsed_time))
        if elapsed_str.startswith('0:'):
            elapsed_str = elapsed_str[2:]  # 移除前置的 '0:'
            
        # 總時長
        if self.durations.get(self.ctx.guild.id, 0) > 0:
            total_str = str(timedelta(seconds=self.durations[self.ctx.guild.id]))
            if total_str.startswith('0:'):
                total_str = total_str[2:]  # 移除前置的 '0:'
                 
            # 計算進度條
            progress_bar_length = 20
            filled_length = min(progress_bar_length, int(progress_bar_length * elapsed_time / self.durations[self.ctx.guild.id]))
            bar = '▰' * filled_length + '▱' * (progress_bar_length - filled_length)
            
            # 計算百分比
            percentage = min(100, int((elapsed_time / self.durations[self.ctx.guild.id]) * 100)) if self.durations[self.ctx.guild.id] > 0 else 0
            
            embed.add_field(
                name="進度", 
                value=f"`{elapsed_str} / {total_str}`\n`{bar}`", 
                inline=False
            )
        else:
            embed.add_field(
                name="進度", 
                value=f"已播放: `{elapsed_str}`\n無法獲取總時長", 
                inline=False
            )
        
        # 顯示循環狀態
        loop_status = "開啟 🔁" if self.loop_mode.get(self.ctx.guild.id, False) else "關閉 ▶️"
        embed.add_field(name="循環模式", value=loop_status)
        
        # 顯示隊列信息
        queue_status = f"隊列中還有 {len(self.queues.get(self.ctx.guild.id, []))} 首歌曲"
        embed.add_field(name="隊列", value=queue_status)
        
        # 如果有歌曲封面，則添加
        if 'thumbnail' in self.current.get(self.ctx.guild.id) and self.current[self.ctx.guild.id]['thumbnail']:
            embed.set_thumbnail(url=self.current[self.ctx.guild.id]['thumbnail'])
            
        return embed

    async def play_next(self, guild_id):
        if self.voice_clients.get(guild_id) and self.voice_clients[guild_id].is_connected():
            # 檢查是否處於循環模式
            if self.loop_mode.get(guild_id, False) and self.current.get(guild_id):
                # 將當前歌曲添加到隊列的最前面
                if guild_id not in self.queues:
                    self.queues[guild_id] = []
                self.queues[guild_id].insert(0, self.current[guild_id])
            
            if guild_id in self.queues and len(self.queues[guild_id]) > 0:
                # 從隊列中取出下一首歌
                next_song = self.queues[guild_id].pop(0)
                self.current[guild_id] = next_song
                
                # 更新開始時間和持續時間
                self.start_times[guild_id] = datetime.now()
                self.durations[guild_id] = next_song.get('duration', 0)
                
                print(f"開始播放: {next_song.get('title', '未知')} - 持續時間: {next_song.get('duration', 0)}秒")
                
                # 播放音樂
                try:
                    # 設置FFmpeg選項
                    ffmpeg_options = {
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        'options': '-vn'
                    }
                    
                    # 若找到ffmpeg路徑，則加入到選項
                    if self.ffmpeg_path:
                        ffmpeg_options['executable'] = self.ffmpeg_path
                    
                    # 創建音頻源
                    source = discord.FFmpegPCMAudio(next_song['url'], **ffmpeg_options)
                    
                    # 播放音頻
                    self.voice_clients[guild_id].play(
                        source, 
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            self.play_next(guild_id), self.bot.loop
                        )
                    )
                    
                    # 更新控制面板
                    if guild_id in self.player_contexts and guild_id in self.control_messages:
                        ctx = self.player_contexts[guild_id]
                        view = MusicControlView(self, ctx)
                        view.message = self.control_messages[guild_id]
                        await view.update_player()
                    else:
                        # 如果沒有控制面板但有上下文，則創建一個
                        if guild_id in self.player_contexts:
                            await self.show_player(self.player_contexts[guild_id])
                except Exception as e:
                    print(f"播放音樂時發生錯誤: {e}")
                    
                    if guild_id in self.player_contexts:
                        await self.player_contexts[guild_id].send(f"播放時發生錯誤: {str(e)}")
                    
                    # 嘗試播放下一首
                    await self.play_next(guild_id)
            else:
                # 隊列中沒有更多歌曲
                print(f"隊列中沒有更多歌曲")
                self.current[guild_id] = None
                self.start_times[guild_id] = None
                self.durations[guild_id] = None
                
                # 更新控制面板
                if guild_id in self.player_contexts and guild_id in self.control_messages:
                    ctx = self.player_contexts[guild_id]
                    view = MusicControlView(self, ctx)
                    view.message = self.control_messages[guild_id]
                    await view.update_player()

    @commands.command(name='join')
    async def join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("你必須先加入一個語音頻道!")
            return
            
        channel = ctx.message.author.voice.channel
        
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
        
        try:
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect()
                await asyncio.sleep(2)
                
            voice_client = await channel.connect()
            await ctx.send(f"已加入 {channel.name}!")
            
        except Exception as e:
            await ctx.send(f"加入頻道時發生錯誤: {str(e)}")
            print(f"Voice connection error: {str(e)}")

    @commands.command(name='play')
    async def play(self, ctx, *, query=None):
        """播放歌曲"""
        if not ctx.author.voice:
            await ctx.send('你必須加入一個語音頻道才能使用這個指令')
            return
        
        if not query:
            await ctx.send('請提供歌曲名稱或URL')
            return
        
        voice_channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        
        # 加入語音頻道
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            self.voice_clients[guild_id] = await voice_channel.connect()
        elif self.voice_clients[guild_id].channel != voice_channel:
            await self.voice_clients[guild_id].move_to(voice_channel)
        
        # 顯示正在搜尋的訊息
        searching_msg = await ctx.send(f'🔍 正在搜尋: {query}')
        
        # 處理YouTube Music連結
        if 'music.youtube.com' in query:
            query = query.replace('music.youtube.com', 'www.youtube.com')
            print(f"轉換YouTube Music URL: {query}")
        
        # 下載並獲取歌曲信息
        try:
            # 改進URL檢測正則表達式，包含更多YouTube URL格式
            is_url = re.match(r'^(https?://)?(www\.|music\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/playlist\?list=)([a-zA-Z0-9_-]+)', query)
            
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ytdl:
                if not is_url:
                    # 搜尋模式時，先檢查搜尋結果是否為空
                    search_result = ytdl.extract_info(f"ytsearch:{query}", download=False)
                    if not search_result or 'entries' not in search_result or len(search_result['entries']) == 0:
                        await searching_msg.edit(content=f'❌ 無法找到符合 "{query}" 的結果')
                    return
                    info = search_result['entries'][0]
            else:
                    # 直接URL模式
                    info = ytdl.extract_info(query, download=False)
            
            # 處理播放清單URL的情況
            if info and 'entries' in info:
                # 這是一個播放清單
                await searching_msg.edit(content=f'⚠️ 這似乎是一個播放清單。請使用 `$$playlist {query}` 來播放整個清單，或選擇單個視頻來播放。')
                return
            
            # 檢查info是否有效
            if not info:
                await searching_msg.edit(content=f'❌ 無法解析該影片信息')
                return

            # 確保必要的字段存在
            if 'url' not in info or 'title' not in info:
                await searching_msg.edit(content=f'❌ 影片信息不完整，無法播放')
                return
            
            song_info = {
                'url': info['url'],
                'title': info['title'],
                'duration': info.get('duration', 0),
                'webpage_url': info.get('webpage_url', ''),
                'thumbnail': info.get('thumbnail', '')  # 加入縮圖URL
            }
            
            # 將歌曲添加到隊列
            if guild_id not in self.queues:
                self.queues[guild_id] = []
            self.queues[guild_id].append(song_info)
            
            # 更新搜尋訊息
            await searching_msg.edit(content=f'✅ 已將 **{song_info["title"]}** 添加到隊列')
            
            # 保存當前上下文以便更新控制面板
            self.player_contexts[guild_id] = ctx
            
            # 如果沒有正在播放的歌曲，則播放這首歌
            if not self.voice_clients[guild_id].is_playing() and not self.voice_clients[guild_id].is_paused():
                await self.play_next(guild_id)
                
            # 無論如何都重新顯示控制面板
            await self.refresh_player(ctx)
                    
        except Exception as e:
            error_msg = str(e)
            await searching_msg.edit(content=f'❌ 發生錯誤: {error_msg[:1500] if len(error_msg) > 1500 else error_msg}')
            print(f"播放歌曲時發生錯誤: {e}")

    @commands.command(name='leave')
    async def leave(self, ctx):
        """離開語音頻道"""
        guild_id = ctx.guild.id
        
        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
            await self.voice_clients[guild_id].disconnect()
            self.voice_clients[guild_id] = None
            self.queues[guild_id] = []
            self.current[guild_id] = None
            self.start_times[guild_id] = None
            self.durations[guild_id] = None
            await ctx.send('已離開語音頻道')
            
            # 更新控制面板
            if guild_id in self.player_contexts and guild_id in self.control_messages:
                try:
                    view = MusicControlView(self, self.player_contexts[guild_id])
                    view.message = self.control_messages[guild_id]
                    await view.update_player()
                except Exception as e:
                    print(f"更新播放器控制面板時發生錯誤: {e}")
        else:
            await ctx.send('機器人不在語音頻道中')

    @commands.command(name='pause')
    async def pause(self, ctx):
        """暫停音樂"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("音樂已暫停!")
            # 更新控制面板
            await self.update_player()

    @commands.command(name='resume')
    async def resume(self, ctx):
        """繼續播放"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("繼續播放!")
            # 更新控制面板
            await self.update_player()

    @commands.command(name='queue')
    async def queue(self, ctx):
        """顯示播放隊列"""
        if len(self.queues.get(ctx.guild.id, [])) == 0:
            await ctx.send('播放隊列是空的!')
            return
        
        queue_list = '\n'.join([f'{i+1}. {song["title"]}' for i, song in enumerate(self.queues[ctx.guild.id])])
        
        if len(queue_list) > 2000:
            chunks = [queue_list[i:i+2000] for i in range(0, len(queue_list), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(f'當前播放隊列:\n{queue_list}')

    @commands.command(name='skip')
    async def skip(self, ctx):
        """跳過當前歌曲"""
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send('已跳過當前歌曲!')

    @commands.command(name='clear')
    async def clear(self, ctx):
        """清空播放隊列"""
        self.queues[ctx.guild.id] = []
        await ctx.send('播放隊列已清空!')
        # 更新控制面板
        await self.update_player()

    @commands.command(name='loop')
    async def loop(self, ctx):
        """切換循環模式"""
        await self.toggle_loop(ctx)

    @commands.command(name='player')
    async def player(self, ctx):
        """顯示音樂播放器控制面板"""
        await self.refresh_player(ctx)

    @commands.command(name='progress')
    async def progress(self, ctx):
        """顯示當前歌曲播放進度"""
        if not ctx.voice_client or not self.current.get(ctx.guild.id) or not self.start_times.get(ctx.guild.id):
            await ctx.send("目前沒有播放歌曲！")
            return
            
        # 直接調用播放器命令以顯示完整控制面板
        await self.player(ctx)

    async def process_playlist_entries(self, ctx, entries, start_idx, end_idx):
        """處理播放清單中的歌曲"""
        success_count = 0
        failed_songs = []
        guild_id = ctx.guild.id
        
        for i, entry in enumerate(entries[start_idx:end_idx]):
            try:
                if entry is None:
                    continue
                    
                # 確保entry有id字段
                if 'id' not in entry:
                    failed_songs.append(entry.get('title', '未知歌曲'))
                    continue
                
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                
                try:
                video_info = await asyncio.get_event_loop().run_in_executor(
                    None,
                        lambda: yt_dlp.YoutubeDL(self.ytdl_opts).extract_info(video_url, download=False)
                    )
                    
                    if not video_info or 'url' not in video_info or 'title' not in video_info:
                        failed_songs.append(entry.get('title', f'ID: {entry.get("id", "未知")}'))
                        continue
                
                song = {
                    'url': video_info['url'],
                        'title': video_info['title'],
                        'duration': video_info.get('duration', 0),
                        'webpage_url': video_info.get('webpage_url', ''),
                        'thumbnail': video_info.get('thumbnail', '')
                    }
                        
                    if guild_id not in self.queues:
                        self.queues[guild_id] = []
                            
                    self.queues[guild_id].append(song)
                success_count += 1
                
                except Exception as inner_e:
                    print(f"處理播放清單項目時發生錯誤: {inner_e}")
                    failed_songs.append(entry.get('title', f'ID: {entry.get("id", "未知")}'))
                    continue
                    
            except Exception as e:
                failed_songs.append(entry.get('title', f'ID: {entry.get("id", "未知")}'))
                print(f"處理播放清單項目時發生錯誤: {e}")
                continue
                
        return success_count, failed_songs

    async def process_remaining_songs(self, ctx, entries, start_idx):
        """背景處理剩餘的歌曲"""
        try:
            total_remaining = len(entries) - start_idx
            if total_remaining <= 0:
                return
                
            success_count, failed_songs = await self.process_playlist_entries(ctx, entries, start_idx, len(entries))
            
            status_message = f"背景處理完成! 已額外加入 {success_count} 首歌曲到播放隊列"
            if failed_songs:
                status_message += f"\n無法處理 {len(failed_songs)} 首歌曲"
            
            await ctx.send(status_message)
            
        except Exception as e:
            await ctx.send("背景處理其餘歌曲時發生錯誤")
            print(f"背景處理錯誤: {str(e)}")

    @commands.command(name='playlist')
    async def playlist(self, ctx, url):
        """播放整個播放清單"""
        if not ctx.author.voice:
            await ctx.send('你必須加入一個語音頻道才能使用這個指令')
                return

        voice_channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        
        # 加入語音頻道
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            self.voice_clients[guild_id] = await voice_channel.connect()
        elif self.voice_clients[guild_id].channel != voice_channel:
            await self.voice_clients[guild_id].move_to(voice_channel)

        # 處理YouTube Music連結
        if 'music.youtube.com' in url:
            url = url.replace('music.youtube.com', 'www.youtube.com')
            print(f"轉換YouTube Music URL: {url}")

        await ctx.send("正在處理播放清單...")
        
        try:
            playlist_opts = self.ytdl_opts.copy()
            playlist_opts.update({
                'ignoreerrors': True,
                'extract_flat': True,
            })
            
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    await ctx.send("❌ 無法解析播放清單信息")
                    return
                
                if 'entries' in info:
                    entries = [entry for entry in info['entries'] if entry is not None]
                    total_songs = len(entries)
                    
                    if total_songs == 0:
                        await ctx.send("無法從播放清單中找到任何可用的歌曲。")
                        return
                        
                    initial_batch = min(5, total_songs)
                    await ctx.send(f"開始處理前 {initial_batch} 首歌曲...")
                    
                    # 確保guild_id在隊列中存在
                    if guild_id not in self.queues:
                        self.queues[guild_id] = []
                    
                    success_count, failed_songs = await self.process_playlist_entries(ctx, entries, 0, initial_batch)
                    
                    status_message = f"已加入 {success_count} 首歌曲到播放隊列並開始播放!"
                    if failed_songs:
                        status_message += f"\n無法處理 {len(failed_songs)} 首歌曲"
                    if total_songs > initial_batch:
                        status_message += f"\n將在背景繼續處理剩餘 {total_songs - initial_batch} 首歌曲..."
                    
                    await ctx.send(status_message)
                    
                    # 保存上下文
                    self.player_contexts[guild_id] = ctx
                    
                    # 開始播放
                    if guild_id in self.voice_clients and not self.voice_clients[guild_id].is_playing() and guild_id in self.queues and len(self.queues[guild_id]) > 0:
                        await self.play_next(guild_id)
                        
                        # 自動顯示音樂播放器控制面板
                        await self.show_player(ctx)
                    
                    if total_songs > initial_batch:
                        asyncio.create_task(self.process_remaining_songs(ctx, entries, initial_batch))
                    
                else:
                    await ctx.send("這似乎不是一個播放清單連結。請使用 $$play 指令來播放單一歌曲。")
                    
        except Exception as e:
            error_msg = str(e)
            await ctx.send(f"處理播放清單時發生錯誤，請確認連結是否正確: {error_msg[:100]}")
            print(f"播放清單錯誤: {str(e)}")  # 為了調試添加詳細錯誤輸出

    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        """隨機播放隊列"""
        if len(self.queues.get(ctx.guild.id, [])) > 1:
            random.shuffle(self.queues[ctx.guild.id])
            await ctx.send('播放隊列已隨機排序!')
        else:
            await ctx.send('播放隊列中沒有足夠的歌曲來隨機排序!')

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")
        
    def cog_unload(self):
        """卸載Cog時停止任務"""
        # 取消注册按钮處理函数
        self.bot.remove_listener(self.button_callback, "on_interaction")

    async def toggle_loop(self, ctx):
        """切換循環模式的內部方法"""
        guild_id = ctx.guild.id
        
        # 切換循環模式
        if guild_id not in self.loop_mode:
            self.loop_mode[guild_id] = False
        
        self.loop_mode[guild_id] = not self.loop_mode[guild_id]
        
        # 發送通知
        status = "開啟" if self.loop_mode[guild_id] else "關閉"
        await ctx.send(f'🔁 循環模式已{status}')

    async def previous_song(self, ctx):
        """播放上一首歌曲"""
        guild_id = ctx.guild.id
        
        # 目前還沒有實現記錄歷史播放列表的功能
        # 這裡只是一個簡單的示例，實際上會返回一個訊息
        await ctx.send("⏮️ 上一首功能尚未實現")

    def get_progress_info(self, guild_id):
        """取得當前播放進度信息"""
        if (guild_id not in self.start_times or 
            self.start_times[guild_id] is None or 
            guild_id not in self.durations or 
            self.durations[guild_id] is None or
            self.durations[guild_id] <= 0):
            # 檢查是否正在播放但沒有時間信息
            if (guild_id in self.voice_clients and 
                self.voice_clients[guild_id] and 
                (self.voice_clients[guild_id].is_playing() or self.voice_clients[guild_id].is_paused())):
                print(f"警告: 伺服器 {guild_id} 正在播放但無法獲取進度信息")
            return None
            
        current_time = datetime.now() - self.start_times[guild_id]
        elapsed_seconds = int(current_time.total_seconds())
        
        # 確保不超過總時長
        duration = self.durations[guild_id]
        if duration <= 0:
            return None
            
        if elapsed_seconds > duration:
            elapsed_seconds = duration
            
        # 計算百分比
        percentage = min(100, int((elapsed_seconds / duration) * 100))
        
        # 格式化時間
        elapsed_str = str(timedelta(seconds=elapsed_seconds))
        if elapsed_str.startswith('0:'):
            elapsed_str = elapsed_str[2:]
            
        duration_str = str(timedelta(seconds=duration))
        if duration_str.startswith('0:'):
            duration_str = duration_str[2:]
            
        return (elapsed_str, duration_str, percentage)
    
    def create_progress_bar(self, percentage, length=20):
        """創建進度條 - YouTube Music風格"""
        # 計算指示器位置（四捨五入到最近的位置）
        position = round(percentage * length / 100)
        position = min(position, length)  # 確保不超過長度
        
        # 創建YouTube Music風格的進度條
        # 用"─"創建線，用"⚪"創建移動的點
        if position == 0:
            # 還沒開始播放
            bar = "─" * length
            # bar += " 🔘"
        elif position >= length:
            # 播放完畢
            bar = "─" * length
            bar += "🔘 "
        else:
            # 播放中
            before = "─" * position
            after = "─" * (length - position)
            bar = f"{before}🔘{after}"
        
        return f"`{bar}`"

    @commands.command(name='stop')
    async def stop(self, ctx):
        """停止播放並清空隊列"""
        guild_id = ctx.guild.id
        
        if guild_id in self.voice_clients and self.voice_clients[guild_id] and self.voice_clients[guild_id].is_playing():
            self.voice_clients[guild_id].stop()
            self.current[guild_id] = None
            self.start_times[guild_id] = None
            self.durations[guild_id] = None
            
        if guild_id in self.queues:
            self.queues[guild_id] = []
            
        await ctx.send("已停止播放並清空隊列")
        
        # 更新控制面板
        if guild_id in self.player_contexts and guild_id in self.control_messages:
            try:
                ctx = self.player_contexts[guild_id]
                view = MusicControlView(self, ctx)
                view.message = self.control_messages[guild_id]
                await view.update_player()
            except Exception as e:
                print(f"更新播放器控制面板時發生錯誤: {e}")

    @commands.command(name='refresh')
    async def refresh_player_cmd(self, ctx):
        """重新顯示音樂播放器控制面板在當前位置"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            await ctx.send("機器人目前不在語音頻道中")
            return
            
        if guild_id not in self.current or not self.current[guild_id]:
            await ctx.send("目前沒有播放任何歌曲")
            return
            
        await self.refresh_player(ctx)
        await ctx.send("已刷新播放器控制面板！", delete_after=2)

    async def refresh_player(self, ctx):
        """刷新播放器控制面板（刪除舊的並創建新的）"""
        guild_id = ctx.guild.id
        
        # 如果已經有控制面板，嘗試刪除它
        if guild_id in self.control_messages:
            try:
                await self.control_messages[guild_id].delete()
                print(f"已刪除舊的控制面板")
            except Exception as e:
                print(f"刪除舊控制面板時發生錯誤: {e}")
        
        # 創建新的控制面板
        await self.show_player(ctx)
        
    async def show_player(self, ctx):
        """顯示音樂播放器控制面板"""
        guild_id = ctx.guild.id
        
        # 確保只有在播放音樂時才顯示
        if not self.voice_clients.get(guild_id) or not self.current.get(guild_id):
            await ctx.send("目前沒有播放任何歌曲")
            return
        
        # 創建控制面板View
        view = MusicControlView(self, ctx)
        
        # 創建嵌入式訊息
        embed = discord.Embed(title="🎵 音樂播放器", color=discord.Color.purple())
        
        current = self.current[guild_id]
        
        # 播放狀態
        vc = self.voice_clients[guild_id]
        status = "▶️"
        
        # 循環狀態
        loop_status = "🔁 循環模式: 開啟" if self.loop_mode.get(guild_id, False) else "🔁 循環模式: 關閉"
        
        # 進度條
        progress_info = self.get_progress_info(guild_id)
        if progress_info:
            current_time, duration, percentage = progress_info
            progress_bar = self.create_progress_bar(percentage)
        else:
            current_time = "00:00"
            duration = "00:00"
            progress_bar = "`──────────────────────`"
        
        # 當前歌曲資訊
        title = current.get('title', '未知歌曲')
        url = current.get('webpage_url', '')
        
        embed.description = f"**正在播放:** [{title}]({url})\n\n{loop_status}\n\n{status}  {current_time}  {progress_bar}  {duration}"
        
        # 如果有縮圖
        if 'thumbnail' in current and current['thumbnail']:
            embed.set_thumbnail(url=current['thumbnail'])
        
        # 展示隊列中的下一首歌曲
        queue = self.queues.get(guild_id, [])
        if queue and len(queue) > 0:
            next_songs = list(islice(queue, 0, 3))
            queue_text = "\n".join([f"{i+1}. {song.get('title', '未知歌曲')}" for i, song in enumerate(next_songs)])
            if len(queue) > 3:
                queue_text += f"\n... 還有 {len(queue) - 3} 首歌"
            embed.add_field(name="播放隊列", value=queue_text, inline=False)
        
        # 發送控制面板
        control_message = await ctx.send(embed=embed, view=view)
        view.message = control_message
        
        # 儲存上下文和訊息以便後續更新
        self.player_contexts[guild_id] = ctx
        self.control_messages[guild_id] = control_message

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
