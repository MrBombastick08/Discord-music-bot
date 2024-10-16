import disnake
from disnake.ext import commands
import yt_dlp
import asyncio

# Твой токен
TOKEN = "YOUR_TOKEN"

# Настройки для бота
intents = disnake.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Подключение к голосовому каналу и воспроизведение музыки
@bot.slash_command(description="Проиграть музыку с YouTube")
async def play(inter, url: str):
    channel = inter.author.voice.channel
    if not channel:
        await inter.response.send_message("Вы должны быть в голосовом канале!")
        return

    voice_client = disnake.utils.get(bot.voice_clients, guild=inter.guild)

    if not voice_client:
        voice_client = await channel.connect()

    # Отправляем сообщение, что начали загрузку
    await inter.response.defer()

    # Настройки для yt_dlp (без сохранения файлов)
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': 'True',
        'quiet': True,
        'extract_flat': 'in_playlist',
        'outtmpl': 'audio',  # Не сохраняем файл, используем напрямую для стриминга
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['url']

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    voice_client.play(disnake.FFmpegPCMAudio(url2, **ffmpeg_options), after=lambda e: print('Завершено воспроизведение'))

    # Уведомляем пользователя, что трек играет
    await inter.edit_original_message(content=f"Играет: {info['title']}")

# Запуск бота
bot.run(TOKEN)
