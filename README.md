# Музыкальный бот для Discord (ПРОЕКТ БРОШЕН, в связи блокировкой Discord на территории РФ)

Этот бот создан для воспроизведения музыки из YouTube в голосовых каналах Discord, используя библиотеки `disnake` и `yt-dlp`. Бот обеспечивает потоковое воспроизведение без необходимости сохранять файлы на диск.

## Необходимые инструменты

1. Python версии 3.8 или выше — [Загрузить Python](https://www.python.org/downloads/)
2. [FFmpeg](https://ffmpeg.org/download.html) — для работы с аудио в реальном времени
3. ОБЯЗАТЕЛЬНО установить виртуальную среду (.venv)
4. Python-библиотеки:
   - disnake
   - yt-dlp

## Установка

1. Скачайте или клонируйте репозиторий на ваше устройство.
2. Установите необходимые библиотеки с помощью `pip`:

```bash
pip install disnake yt-dlp
```

3. Убедитесь, что вы установили FFmpeg и добавили его в системные переменные (PATH). Это можно проверить, введя в командной строке:

```bash
ffmpeg -version
```

4. Откройте файл с кодом бота (`main.py` или аналогичный) и вставьте токен вашего Discord бота:

```python
TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
```

## Запуск бота

1. Чтобы запустить бота, выполните следующую команду:

```bash
python main.py
```

2. После запуска бота можно использовать следующие команды:

### Основные функции

- `/play <URL>` — бот подключается к голосовому каналу и начинает воспроизводить музыку из указанного YouTube URL. 
```

