import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN não encontrado no ambiente")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"🔥 BOT ONLINE 🔥 | {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ {len(synced)} comandos sincronizados GLOBALMENTE")


async def main():
    async with bot:
        await bot.load_extension("cogs.whitelist")
        print("✅ Cog whitelist carregado")
        await bot.start(TOKEN)


asyncio.run(main())