import disnake
from disnake.ext import commands
from googleapiclient.discovery import build
import yt_dlp
import asyncio

# 🔐 Токены
DISCORD_TOKEN = "TOKEN" # Токен вашего бота Discord
YOUTUBE_API_KEY = "TOKEN" # Ключ API YouTube Data v3

# Настраиваем намерения бота (что он может делать и какие события слушать)
intents = disnake.Intents.default()
intents.message_content = True # Разрешаем боту читать содержимое сообщений (для команд)
intents.voice_states = True # Разрешаем боту отслеживать состояние голосовых каналов (кто куда зашел/вышел)

# Создаем экземпляр бота с нашими намерениями
bot = commands.InteractionBot(intents=intents)
# Инициализируем клиент YouTube API для поиска видео
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Класс для управления музыкальным плеером в рамках одного сервера (гильдии)
class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id # ID сервера, к которому относится этот плеер
        self.queue = [] # Очередь треков для воспроизведения
        self.current = None # Текущий воспроизводимый трек
        self.position = 0 # Позиция в очереди (для отслеживания, какой трек следующий)
        self.is_playing = False # Флаг, показывающий, играет ли что-то сейчас

    # Добавляем трек в конец очереди
    def add_to_queue(self, track):
        self.queue.append(track)

    # Очищаем всю очередь и сбрасываем состояние плеера
    def clear_queue(self):
        self.queue.clear()
        self.current = None
        self.position = 0
        self.is_playing = False

    # Получаем следующий трек из очереди
    def get_next_track(self):
        if self.position < len(self.queue):
            track = self.queue[self.position]
            self.current = track
            self.position += 1
            return track
        return None # Если очередь пуста или закончилась

# Словарь для хранения экземпляров MusicPlayer для каждого сервера
players = {}

# Функция для получения или создания экземпляра MusicPlayer для конкретного сервера
def get_player(guild_id):
    if guild_id not in players:
        players[guild_id] = MusicPlayer(guild_id) # Если плеера для сервера нет, создаем новый
    return players[guild_id]

# Функция для получения прямой ссылки на аудиопоток из видео (используем yt-dlp)
def get_audio_stream(url):
    ydl_opts = {
        'format': 'bestaudio', # Выбираем лучшее аудио качество
        'quiet': True, # Не выводим лишнюю информацию в консоль
        'no_warnings': True, # Отключаем предупреждения
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False) # Получаем информацию о видео без скачивания
            if 'entries' in info: # Если это плейлист, берем первый трек
                return info['entries'][0]['url']
            return info['url'] # Если это одно видео, берем его URL
    except Exception as e:
        print(f"❌ yt-dlp error: {e}") # Логируем ошибку, если что-то пошло не так
        return None

# Функция для получения элементов плейлиста YouTube
def get_playlist_items(url, limit=10):
    ydl_opts = {
        'quiet': True,
        'extract_flat': False, # Важно, чтобы получить полную информацию о каждом видео
        'skip_download': True, # Нам не нужно скачивать видео, только метаданные
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist = ydl.extract_info(url, download=False) # Получаем информацию о плейлисте
        if "entries" not in playlist:
            return [] # Если плейлист пуст или не найден
        return [
            {
                "title": entry.get("title"),
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}" # Формируем URL видео
            }
            for entry in playlist["entries"][:limit] # Берем только указанное количество треков
            if entry
        ]

# Асинхронная функция для поиска видео на YouTube с помощью YouTube Data API
async def search_youtube(query: str):
    request = youtube.search().list(
        part="snippet", # Нам нужен сниппет (заголовок, описание и т.д.)
        maxResults=1, # Ищем только одно видео
        q=query, # Наш поисковый запрос
        type="video" # Ищем именно видео
    )
    response = request.execute() # Выполняем запрос

    if not response["items"]:
        return None # Если ничего не найдено

    item = response["items"][0] # Берем первый результат
    video_id = item["id"]["videoId"] # Извлекаем ID видео
    return {
        "title": item["snippet"]["title"], # Заголовок видео
        "url": f"https://www.youtube.com/watch?v={video_id}" # URL видео
    }

# Событие, которое срабатывает, когда бот готов к работе
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен и готов к работе!") # Приветственное сообщение
    await bot.sync_application_commands() # Синхронизируем слеш-команды с Discord

# Слеш-команда для воспроизведения музыки или плейлиста
@bot.slash_command(description="🎵 Воспроизвести музыку или плейлист с YouTube")
async def start(inter: disnake.ApplicationCommandInteraction, query: str):
    await inter.response.defer() # Откладываем ответ, чтобы бот не показал ошибку таймаута

    if not inter.author.voice:
        await inter.followup.send("❗ Вы должны находиться в голосовом канале.") # Проверяем, находится ли пользователь в голосовом канале
        return

    channel = inter.author.voice.channel # Получаем голосовой канал пользователя
    guild_id = inter.guild.id # Получаем ID сервера
    music_player = get_player(guild_id) # Получаем или создаем плеер для этого сервера

    vc = inter.guild.voice_client or await channel.connect() # Подключаемся к голосовому каналу, если еще не подключены

    if "list=" in query: # Проверяем, является ли запрос ссылкой на плейлист
        await inter.channel.send("📂 Обнаружен плейлист. Загружаю...")
        try:
            tracks = get_playlist_items(query) # Пытаемся загрузить треки из плейлиста
            if not tracks:
                await inter.channel.send("❌ Не удалось загрузить плейлист.")
                return
            for t in tracks:
                music_player.add_to_queue(t) # Добавляем каждый трек в очередь
            await inter.channel.send(f"✅ Добавлено {len(tracks)} треков.")
        except Exception as e:
            await inter.channel.send(f"❌ Ошибка: {e}") # Логируем ошибку загрузки плейлиста
            return
    else:
        track = await search_youtube(query) # Ищем видео на YouTube по запросу
        if not track:
            await inter.channel.send("❌ Видео не найдено.")
            return
        music_player.add_to_queue(track) # Добавляем найденный трек в очередь
        await inter.channel.send(f"✅ Добавлено: `{track["title"]}`")

    if not music_player.is_playing: # Если ничего не играет, начинаем воспроизведение
        next_track = music_player.get_next_track() # Берем следующий трек из очереди
        if next_track:
            stream_url = get_audio_stream(next_track["url"]) # Получаем прямую ссылку на аудиопоток
            if not stream_url:
                await inter.channel.send(f"❌ Не удалось получить ссылку для `{next_track["title"]}`")
                music_player.is_playing = False
                return
            # Воспроизводим аудио и устанавливаем функцию обратного вызова для следующего трека
            vc.play(disnake.FFmpegPCMAudio(stream_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(vc, guild_id), bot.loop))
            music_player.is_playing = True # Устанавливаем флаг, что плеер играет
            await inter.channel.send(f"🎶 Сейчас играет: `{next_track["title"]}`")

# Альтернативная команда для воспроизведения (просто вызывает команду start)
@bot.slash_command(description="🎵 Альтернатива /start")
async def play(inter: disnake.ApplicationCommandInteraction, query: str):
    await start(inter, query)

# Асинхронная функция для воспроизведения следующего трека в очереди
async def play_next(vc, guild_id):
    music_player = get_player(guild_id)
    next_track = music_player.get_next_track()
    if next_track:
        stream_url = get_audio_stream(next_track["url"])
        if not stream_url:
            print(f"❌ Failed to extract stream: {next_track["title"]}")
            music_player.is_playing = False
            return
        vc.play(disnake.FFmpegPCMAudio(stream_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(vc, guild_id), bot.loop))
    else:
        music_player.is_playing = False # Если треков больше нет, останавливаем плеер
        await vc.disconnect() # Отключаемся от голосового канала

# Слеш-команда для пропуска текущего трека
@bot.slash_command(description="⏭ Пропустить трек")
async def skip(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_playing():
        await inter.followup.send("🚫 Ничего не играет.") # Если ничего не играет, сообщаем об этом
        return
    await inter.followup.send("⏭ Пропускаю...")
    vc.stop() # Останавливаем текущее воспроизведение (это вызовет play_next)

# Слеш-команда для паузы воспроизведения
@bot.slash_command(description="⏸ Пауза")
async def pause(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_playing():
        await inter.followup.send("🚫 Нечего паузить.")
        return
    vc.pause() # Ставим на паузу
    await inter.followup.send("⏸ Пауза.")

# Слеш-команда для возобновления воспроизведения
@bot.slash_command(description="▶️ Возобновить")
async def resume(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc or not vc.is_paused():
        await inter.followup.send("🚫 Не на паузе.")
        return
    vc.resume() # Возобновляем
    await inter.followup.send("▶️ Продолжаем.")

# Слеш-команда для остановки воспроизведения и выхода из канала
@bot.slash_command(description="🛑 Остановить и выйти")
async def stop(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    vc = inter.guild.voice_client
    if not vc:
        await inter.followup.send("❗ Бот не в канале.")
        return
    await vc.disconnect() # Отключаемся от голосового канала
    get_player(inter.guild.id).clear_queue() # Очищаем очередь для этого сервера
    await inter.followup.send("🛑 Остановка и очистка очереди.")

# Слеш-команда для просмотра очереди
@bot.slash_command(description="📜 Очередь")
async def queue(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    music_player = get_player(inter.guild.id)
    if not music_player.queue or music_player.position >= len(music_player.queue):
        await inter.followup.send("📭 Очередь пуста.") # Если очередь пуста
        return
    lines = []
    if music_player.current:
        lines.append(f"**Сейчас играет:** `{music_player.current["title"]}`") # Показываем текущий трек
    for i, track in enumerate(music_player.queue[music_player.position:], start=1):
        lines.append(f"{i}. `{track["title"]}`") # Выводим остальные треки в очереди
    await inter.followup.send("\n".join(lines)) # Отправляем очередь в виде сообщения

# Точка входа в программу: запускаем бота
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)


