import disnake
from disnake.ext import commands
import yt_dlp

TOKEN = "MTI5MDE2MDAyNjg1Nzc3MTAzOA.GbEH1L.a9P726i0h7-mkGeZEigajPBO5yrbOQyjzWM5EY"

intents = disnake.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Функция для скачивания аудио с YouTube
async def from_url(url: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extract_flat': 'in_playlist',
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0',
        'skip_download': True,  # Не скачивать, а передавать поток
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [info])
        for f in formats:
            if f.get('vcodec') == 'none':  # Только аудио
                return f['url']

# Команда /play для воспроизведения аудио
@bot.slash_command()
async def play(inter, url: str):
    # Присоединение к голосовому каналу
    if not inter.author.voice:
        await inter.response.send_message("Ты должен быть в голосовом канале!")
        return
    channel = inter.author.voice.channel
    if not inter.guild.voice_client:
        vc = await channel.connect()
    else:
        vc = inter.guild.voice_client
    
    # Воспроизведение
    try:
        audio_url = await from_url(url)
        vc.play(disnake.FFmpegPCMAudio(audio_url))
        await inter.send(f"Играю: {url}")
    except Exception as e:
        await inter.send(f"Ошибка: {str(e)}")

# Команда /stop для остановки воспроизведения
@bot.slash_command()
async def stop(inter):
    if inter.guild.voice_client:
        await inter.guild.voice_client.disconnect()
        await inter.send("Музыка остановлена и бот отключён.")

bot.run(TOKEN)
