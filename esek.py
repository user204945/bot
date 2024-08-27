import discord
import os
import asyncio
import yt_dlp
from discord.ext import commands, tasks
from dotenv import load_dotenv
from flask import Flask

def start_flask():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return 'OK', 200

    app.run(port=3000, debug=False, use_reloader=False)

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    INTENDED_CHANNEL_ID = 1275432440823025758

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='?', intents=intents)

    queues = {}
    voice_clients = {}
    yt_dl_options = {'format': 'bestaudio/best'}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_executable = 'ffmpeg'
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a volume=0.25',
        'executable': ffmpeg_executable
    }

    activities_list = [
        '/esek şarkı dinliyor',
        '?yardım',
        '?play'
    ]

    @tasks.loop(seconds=5)
    async def update_activity():
        activity = discord.Streaming(name=activities_list[0], url='https://www.youtube.com/watch?v=5v5w8hLDECc')
        await bot.change_presence(status=discord.Status.dnd, activity=activity)
        activities_list.append(activities_list.pop(0))

    @bot.event
    async def on_ready():
        print(f'{bot.user} bot aktif.')
        await bot.change_presence(status=discord.Status.dnd)
        update_activity.start()

    async def search_youtube(query):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
        if 'entries' in result:
            return result['entries'][0]
        else:
            return None

    async def play_song(guild_id, url):
        if guild_id not in voice_clients:
            raise RuntimeError("Bot is not connected to a voice channel.")

        voice_client = voice_clients[guild_id]
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        song_url = data['url']
        player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)

        def after_playing(_):
            if guild_id in queues and queues[guild_id]['loop']:
                asyncio.run_coroutine_threadsafe(play_song(guild_id, url), bot.loop)
            else:
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(), bot.loop)

        voice_client.play(player, after=after_playing)

    async def is_admin(member):
        return member.guild_permissions.administrator

    @bot.command()
    async def play(ctx, *, query: str):
        if not (await is_admin(ctx.author)) and ctx.channel.id != INTENDED_CHANNEL_ID:
            await ctx.send("Bu komutu sadece belirli bir kanalda kullanabilirsiniz.")
            return

        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
            if channel.guild.id not in voice_clients or not voice_clients[channel.guild.id].is_connected():
                voice_client = await channel.connect()
                voice_clients[channel.guild.id] = voice_client
            else:
                voice_client = voice_clients[channel.guild.id]

            result = await search_youtube(query)
            if result:
                url = result['url']
                title = result['title']
                duration = result['duration']

                embed = discord.Embed(
                    title="Şarkı Bilgisi",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Şarkı Adı", value=title, inline=False)
                embed.add_field(name="Süre", value=f"{duration // 60}:{duration % 60:02d}", inline=False)  # Süreyi formatla

                commands_list = """
                **Komutlar:**
`?play <şarkı adı>`: Şarkıyı çalar.
`?stop`: Çalan şarkıyı durdurur.
`?pause`: Çalan şarkıyı duraklatır.
`?resume`: Duraklatılan şarkıyı devam ettirir.
`?loop`: Şarkının döngüye alınıp alınmayacağını belirler. (Bakımda)
`?yardım`: Yardım mesajını gösterir.
                """
                embed.add_field(name="Yardım", value=commands_list, inline=False)

                await ctx.send(embed=embed)

                await play_song(channel.guild.id, url)
            else:
                await ctx.send("Şarkı bulunamadı.")
        else:
            await ctx.send("Önce bir ses kanalına katılmanız gerekiyor.")

    @bot.command()
    async def stop(ctx):
        if not (await is_admin(ctx.author)) and ctx.channel.id != INTENDED_CHANNEL_ID:
            await ctx.send("Bu komutu sadece belirli bir kanalda kullanabilirsiniz.")
            return

        if ctx.author.voice and ctx.author.voice.channel:
            if ctx.guild.id in voice_clients:
                if voice_clients[ctx.guild.id].is_playing() or voice_clients[ctx.guild.id].is_paused():
                    await ctx.send("Şarkı durduruluyor.")
                    voice_clients[ctx.guild.id].stop()
                    await voice_clients[ctx.guild.id].disconnect()
                    del voice_clients[ctx.guild.id]
                    if ctx.guild.id in queues:
                        del queues[ctx.guild.id]
                else:
                    await ctx.send("Şu anda çalınan bir şarkı yok.")
            else:
                await ctx.send("Önce bir şarkı çalmalısınız.")
        else:
            await ctx.send("Önce bir ses kanalına katılmanız gerekiyor.")

    @bot.command()
    async def pause(ctx):
        if not (await is_admin(ctx.author)) and ctx.channel.id != INTENDED_CHANNEL_ID:
            await ctx.send("Bu komutu sadece belirli bir kanalda kullanabilirsiniz.")
            return

        if ctx.author.voice and ctx.author.voice.channel:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].pause()
                await ctx.send("Şarkı duraklatıldı.")
            else:
                await ctx.send("Şu anda çalınan bir şarkı yok.")
        else:
            await ctx.send("Önce bir ses kanalına katılmanız gerekiyor.")

    @bot.command()
    async def resume(ctx):
        if not (await is_admin(ctx.author)) and ctx.channel.id != INTENDED_CHANNEL_ID:
            await ctx.send("Bu komutu sadece belirli bir kanalda kullanabilirsiniz.")
            return

        if ctx.author.voice and ctx.author.voice.channel:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
                voice_clients[ctx.guild.id].resume()
                await ctx.send("Şarkı devam ettirildi.")
            else:
                await ctx.send("Şu anda duraklatılmış bir şarkı yok.")
        else:
            await ctx.send("Önce bir ses kanalına katılmanız gerekiyor.")

    @bot.command()
    async def yardım(ctx):
        help_message = """
        **Komutlar:**
`?play <şarkı adı>`: Şarkıyı çalar.
`?stop`: Çalan şarkıyı durdurur.
`?pause`: Çalan şarkıyı duraklatır.
`?resume`: Duraklatılan şarkıyı devam ettirir.
`?loop`: Şarkının döngüye alınıp alınmayacağını belirler. (Bakımda)
`?yardım`: Yardım mesajını gösterir.
        """
        await ctx.send(help_message)

    bot.run(TOKEN)
