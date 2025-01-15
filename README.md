# 🤖 Multi-Purpose Discord Bot

<div align="center">

![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Steam](https://img.shields.io/badge/Steam-000000?style=for-the-badge&logo=steam&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

A feature-rich Discord bot combining music playback, game tracking, and notification functionalities.

</div>

## ✨ Features

### 🎵 Music Commands
- `$$play <song>`: Play a song from YouTube
- `$$playlist <playlist url>`: Play the playlist from YouTube
- `$$pause`: Pause current playback 
- `$$resume`: Resume playback
- `$$skip`: Skip current song
- `$$queue`: View music queue
- `$$clear`: Clear the queue
- `$$leave`: Disconnect from voice channel

### 🎮 Steam Integration
- `$$search <game>`: Search Steam games
- `$$connect <Steam ID>`: Link your Steam account
- `$$create`: Create wishlist from Steam
- `$$list`: View tracked games

### 🎯 R6 Siege Stats
- `$$r6 <player>`: View player statistics
- Detailed rank information
- Performance metrics tracking

### ⏰ Elsworld Notifications
- Automated dungeon reminders
- Customizable notification times
- Role-based mentioning system

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- FFmpeg
- Discord Bot Token
- Steam API Key
- IsThereAnyDeal API Key

### Installation

1. Clone the repository
```bash
git clone https://github.com/kevin2001111/DC_BOT.git
cd DC_BOT
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your tokens:
```env
DISCORD_TOKEN=your_discord_token
STEAM_ACCESS_TOKEN=your_steam_token
ISTHEREANYDEAL_API_KEY=your_itad_key
```

4. Run the bot
```bash
python bot.py
```

## ⚙️ Configuration

The bot uses the following configuration files:
- `steam/tracked_games.json`: Steam wishlist tracking
- `steam/dcid_connect_steamid.json`: Discord-Steam ID mappings

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
<div align="center">
Made with ❤️ for Discord Communities
</div>
