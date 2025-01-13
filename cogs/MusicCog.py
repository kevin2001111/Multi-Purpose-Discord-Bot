import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import random

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue = deque()
        self.current_song = None
        self.is_playing = False
        self.total_songs = 0
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'ffmpeg_location': "C:\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe",
        }

    async def play_next(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue.popleft()

            try:
                ctx.voice_client.play(
                    discord.FFmpegPCMAudio(
                        self.current_song['url'],
                        executable="C:\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe",
                        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    ),
                    after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
                )
                await ctx.send(f"正在播放: {self.current_song['title']}")
            except Exception as e:
                await ctx.send(f"播放時發生錯誤: {str(e)}")
                self.is_playing = False
                self.current_song = None
        else:
            self.is_playing = False
            self.current_song = None

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
    async def play(self, ctx, *, query):
        """播放音樂"""
        if not ctx.voice_client:
            if ctx.author.voice:
                try:
                    await ctx.author.voice.channel.connect()
                except Exception as e:
                    await ctx.send(f"無法加入語音頻道: {str(e)}")
                    return
            else:
                await ctx.send("你必須先加入一個語音頻道!")
                return

        try:
            await ctx.send("Loading...")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    if not query.startswith('http'):
                        query = f"ytsearch:{query}"
                    
                    info = ydl.extract_info(query, download=False)
                    
                    if 'entries' in info:
                        info = info['entries'][0]
                    
                    url = info['url']
                    title = info['title']
                    
                    song = {'url': url, 'title': title}
                    self.music_queue.append(song)

                    await ctx.send(f'已加入隊列: {title}')
                    
                    if not self.is_playing:
                        await self.play_next(ctx)
                except Exception as e:
                    await ctx.send(f"無法處理該影片: {str(e)}")
                    print(f"詳細錯誤: {str(e)}")
                    
        except Exception as e:
            await ctx.send(f"發生錯誤: {str(e)}")
            print(f"詳細錯誤: {str(e)}")

    @commands.command(name='leave')
    async def leave(self, ctx):
        """離開語音頻道"""
        if ctx.voice_client:
            self.total_songs = 0
            self.current_song = None
            self.is_playing = False
            self.music_queue.clear()
            await ctx.voice_client.disconnect()
            await ctx.send("已離開語音頻道!")

    @commands.command(name='pause')
    async def pause(self, ctx):
        """暫停音樂"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("音樂已暫停!")

    @commands.command(name='resume')
    async def resume(self, ctx):
        """繼續播放"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("繼續播放!")

    @commands.command(name='queue')
    async def queue(self, ctx):
        """顯示播放隊列"""
        if len(self.music_queue) == 0:
            await ctx.send('播放隊列是空的!')
            return
        
        queue_list = '\n'.join([f'{i+1}. {song["title"]}' for i, song in enumerate(self.music_queue)])
        
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
        self.music_queue.clear()
        await ctx.send('播放隊列已清空!')

    async def process_playlist_entries(self, ctx, entries, start_idx, end_idx):
        """處理播放清單中的歌曲"""
        success_count = 0
        failed_songs = []
        
        for i, entry in enumerate(entries[start_idx:end_idx]):
            try:
                if entry is None:
                    continue
                    
                video_info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: yt_dlp.YoutubeDL(self.ydl_opts).extract_info(
                        f"https://www.youtube.com/watch?v={entry['id']}", 
                        download=False
                    )
                )
                
                song = {
                    'url': video_info['url'],
                    'title': video_info['title']
                }
                self.music_queue.append(song)
                success_count += 1
                
            except Exception as e:
                failed_songs.append(entry.get('title', f'ID: {entry.get("id", "未知")}'))
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
        if not ctx.voice_client:
            if ctx.author.voice:
                try:
                    await ctx.author.voice.channel.connect()
                except Exception as e:
                    await ctx.send(f"無法加入語音頻道: {str(e)}")
                    return
            else:
                await ctx.send("你必須先加入一個語音頻道!")
                return

        if 'music.youtube.com' in url:
            url = url.replace('music.youtube.com', 'www.youtube.com')

        await ctx.send("正在處理播放清單...")
        
        try:
            playlist_opts = self.ydl_opts.copy()
            playlist_opts.update({
                'ignoreerrors': True,
                'extract_flat': True,
            })
            
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    entries = [entry for entry in info['entries'] if entry is not None]
                    total_songs = len(entries)
                    
                    if total_songs == 0:
                        await ctx.send("無法從播放清單中找到任何可用的歌曲。")
                        return
                        
                    initial_batch = min(5, total_songs)
                    await ctx.send(f"開始處理前 {initial_batch} 首歌曲...")
                    
                    success_count, failed_songs = await self.process_playlist_entries(ctx, entries, 0, initial_batch)
                    
                    status_message = f"已加入 {success_count} 首歌曲到播放隊列並開始播放!"
                    if failed_songs:
                        status_message += f"\n無法處理 {len(failed_songs)} 首歌曲"
                    if total_songs > initial_batch:
                        status_message += f"\n將在背景繼續處理剩餘 {total_songs - initial_batch} 首歌曲..."
                    
                    await ctx.send(status_message)
                    
                    if not self.is_playing and len(self.music_queue) > 0:
                        await self.play_next(ctx)
                    
                    if total_songs > initial_batch:
                        asyncio.create_task(self.process_remaining_songs(ctx, entries, initial_batch))
                    
                else:
                    await ctx.send("這似乎不是一個播放清單連結。請使用 $$play 指令來播放單一歌曲。")
                    
        except Exception as e:
            await ctx.send(f"處理播放清單時發生錯誤，請確認連結是否正確。")
            print(f"播放清單錯誤: {str(e)}")  # 為了調試添加詳細錯誤輸出

    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        """隨機播放隊列"""
        if len(self.music_queue) > 1:
            random.shuffle(self.music_queue)
            await ctx.send('播放隊列已隨機排序!')
        else:
            await ctx.send('播放隊列中沒有足夠的歌曲來隨機排序!')

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

def setup(bot):
    bot.add_cog(MusicCog(bot))
