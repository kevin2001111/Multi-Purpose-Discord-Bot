# 🤖 Multi-Purpose Discord Bot

<div align="center">

![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Elsworld](https://img.shields.io/badge/Elsword-FF4500?style=for-the-badge&logo=game&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

</div>

A versatile Discord bot integrating music playback, game tracking, and notification systems. Offers rich interactive experiences to energize your Discord community.

## 🌟 Key Features

### 🎵 Music System
Powerful music playback functionality with YouTube search and playlist support:

- **Basic Controls**: Play, pause, resume, skip, clear queue
- **Interactive Player**: Visual control panel with progress bar
- **Playlist Support**: Easily load and play entire YouTube playlists
- **Loop Mode**: Single track/playlist looping
- **Auto Disconnect**: Automatically leaves voice channels after 30 minutes of inactivity, saving resources

### ⏰ Elsworld Game Reminders
Automated dungeon reminder system so your team never misses important dungeon times:

- **Timed Notifications**: 163-Praegas Maze, 194-Steel Wall timed reminders
- **Custom Scheduling**: Set automatic reminders based on official dungeon timetables
- **Role Tagging**: Automatically tag relevant role groups to ensure everyone receives notifications
- **Visual Cues**: Attractive reminders with dungeon images attached

### 🔄 Extensible Design
Modular design makes the bot easy to extend:

- **Dynamic Module Loading**: Support for hot-swappable feature modules
- **Admin Commands**: Convenient module load/unload/reload functions
- **Asynchronous Processing**: High-performance event handling and command execution

## 📋 Command List

### 🎵 Music Commands
- `$$join` - Join voice channel
- `$$play <song name or URL>` - Play music
- `$$playlist <playlist URL>` - Play an entire YouTube playlist
- `$$pause` - Pause playback
- `$$resume` - Resume playback
- `$$skip` - Skip current song
- `$$queue` - View playback queue
- `$$clear` - Clear the queue
- `$$loop` - Toggle loop mode
- `$$player` - Display interactive music player
- `$$leave` - Leave voice channel

### ⚙️ Admin Commands
- `$$load <module name>` - Load module
- `$$unload <module name>` - Unload module
- `$$reload <module name>` - Reload module
- `$$shutdown` - Safely shut down the bot

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- FFmpeg (for audio processing)
- Discord bot token
- Other optional API keys (depending on features used)

### Installation Steps

1. **Clone the Project**
```bash
git clone https://github.com/kevin2001111/Multi-Purpose-Discord-Bot.git
cd Multi-Purpose-Discord-Bot
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment Variables**
Create a `.env` file and add the necessary tokens and IDs:
```
DISCORD_TOKEN=your_discord_bot_token
ELSWORLD_CHANNEL_ID=notification_channel_id
ELSWORLD_ROLE_ID=notification_role_id
```

4. **Start the Bot**
```bash
python bot.py
```

## 🛠️ Customization

### Elsword Reminder Times
Adjust in `cogs/ElsworldNotificationsCog.py`:
```python
NOTIFICATION_TIMES_163 = [
    (7, 0), (11, 0), (15, 0), 
    (19, 0), (23, 0), (3, 0), 
]
NOTIFICATION_TIMES_194 = [
    (9, 0), (13, 0), (17, 0), 
    (21, 0), (1, 0), (5, 0),
]
```

### Music Playback Settings
Adjust audio quality and other playback settings in `cogs/MusicCog.py`:
```python
self.ytdl_opts = {
    'format': 'bestaudio/best',
    ...
}
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Bug reports and feature suggestions are welcome! Feel free to submit Pull Requests for any improvements.

---
<div align="center">
Made with ❤️ for Discord Communities
</div>
