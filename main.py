import os
import threading
import asyncio
import discord
from discord.ext import commands
from web import start_web

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"🔥 BOT ONLINE 🔥 | {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ {len(synced)} comandos sincronizados GLOBALMENTE")


async def start_bot():
    async with bot:
        await bot.load_extension("cogs.whitelist")
        print("✅ Cog whitelist carregado")
        await bot.start(TOKEN)


if __name__ == "__main__":
    # sobe o web server em outra thread (Render exige porta aberta)
    threading.Thread(target=start_web, daemon=True).start()

    # inicia o bot
    asyncio.run(start_bot())