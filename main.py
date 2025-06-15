import disnake
from disnake.ext import commands
from googleapiclient.discovery import build
import yt_dlp
import asyncio

# 🔐 Токены
DISCORD_TOKEN = "TOKEN"
YOUTUBE_API_KEY = "TOKEN"

intents = disnake.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.InteractionBot(intents=intents)
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = []
        self.current = None
        self.position = 0
        self.is_playing = False

    def add_to_queue(self, track):
        self.queue.append(track)

    def clear_queue(self):
        self.queue.clear()
        self.current = None
        self.position = 0
        self.is_playing = False

    def get_next_track(self):
        if self.position < len(self.queue):
            track = self.queue[self.position]
            self.current = track
            self.position += 1
            return track
        return None

players = {}

def get_player(guild_id):
    if guild_id not in players:
        players[guild_id] = MusicPlayer(guild_id)
    return players[guild_id]

def get_audio_stream(url):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                return info['entries'][0]['url']
            return info['url']
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return None

def get_playlist_items(url, limit=10):
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist = ydl.extract_info(url, download=False)
        if "entries" not in playlist:
            return []
        return [
            {
                "title": entry.get("title"),
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}"
            }
            for entry in playlist["entries"][:limit]
            if entry
        ]

async def search_youtube(query: str):
    request = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=query,
        type="video"
    )
    response = request.execute()

    if not response["items"]:
        return None

    item = response["items"][0]
    video_id = item["id"]["videoId"]
    return {
        "title": item["snippet"]["title"],
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен и готов к работе!")
    await bot.sync_application_commands()

@bot.slash_command(description="🎵 Воспроизвести музыку или плейлист с YouTube")
async def start(inter: disnake.ApplicationCommandInteraction, query: str):
    await inter.response.defer()

    if not inter.author.voice:
        await inter.followup.send("❗ Вы должны находиться в голосовом канале.")
        return

    channel = inter.author.voice.channel
    guild_id = inter.guild.id
    music_player = get_player(guild_id)

    vc = inter.guild.voice_client or await channel.connect()

    if "list=" in query:
        await inter.channel.send("📂 Обнаружен плейлист. Загружаю...")
        try:
            tracks = get_playlist_items(query)
            if not tracks:
                await inter.channel.send("❌ Не удалось загрузить плейлист.")
                return
            for t in tracks:
                music_player.add_to_queue(t)
            await inter.channel.send(f"✅ Добавлено {len(tracks)} треков.")
        except Exception as e:
            await inter.channel.send(f"❌ Ошибка: {e}")
            return
    else:
        track = await search_youtube(query)
        if not track:
            await inter.channel.send("❌ Видео не найдено.")
            return
        music_player.add_to_queue(track)
        await inter.channel.send(f"✅ Добавлено: `{track['title']}`")

    if not music_player.is_playing:
        next_track = music_player.get_next_track()
        if next_track:
            stream_url = get_audio_stream(next_track['url'])
            if not stream_url:
                await inter.channel.send(f"❌ Не удалось получить ссылку для `{next_track['title']}`")
                music_player.is_playing = False
                return
            vc.play(disnake.FFmpegPCMAudio(stream_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(vc, guild_id), bot.loop))
            music_player.is_playing = True
            await inter.channel.send(f"🎶 Сейчас играет: `{next_track['title']}`")

@bot.slash_command(description="🎵 Альтернатива /start")
async def play(inter: disnake.ApplicationCommandInteraction, query: str):
    await start(inter, query)

async def play_next(vc, guild_id):
    music_player = get_player(guild_id)
    next_track = music_player.get_next_track()
    if next_track:
        stream_url = get_audio_stream(next_track['url'])
        if not stream_url:
            print(f"❌ Failed to extract stream: {next_track['title']}")
            music_player.is_playing = False
            return
        vc.play(disnake.FFmpegPCMAudio(stream_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(vc, guild_id), bot.loop))
    else:
        music_player.is_playing = False
        await vc.disconnect()

@bot.slash_command(description="⏭ Пропустить трек")
async def skip(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_playing():
        await inter.followup.send("🚫 Ничего не играет.")
        return
    await inter.followup.send("⏭ Пропускаю...")
    vc.stop()

@bot.slash_command(description="⏸ Пауза")
async def pause(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_playing():
        await inter.followup.send("🚫 Нечего паузить.")
        return
    vc.pause()
    await inter.followup.send("⏸ Пауза.")

@bot.slash_command(description="▶️ Возобновить")
async def resume(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_paused():
        await inter.followup.send("🚫 Не на паузе.")
        return
    vc.resume()
    await inter.followup.send("▶️ Продолжаем.")

@bot.slash_command(description="🛑 Остановить и выйти")
async def stop(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc:
        await inter.followup.send("❗ Бот не в канале.")
        return
    await vc.disconnect()
    get_player(inter.guild.id).clear_queue()
    await inter.followup.send("🛑 Остановка и очистка очереди.")

@bot.slash_command(description="📜 Очередь")
async def queue(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    music_player = get_player(inter.guild.id)
    if not music_player.queue or music_player.position >= len(music_player.queue):
        await inter.followup.send("📭 Очередь пуста.")
        return
    lines = []
    if music_player.current:
        lines.append(f"**Сейчас играет:** `{music_player.current['title']}`")
    for i, track in enumerate(music_player.queue[music_player.position:], start=1):
        lines.append(f"{i}. `{track['title']}`")
    await inter.followup.send("\n".join(lines))

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
