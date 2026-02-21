import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
import time

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN não encontrado")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

PLANOS_FILE = "planos.json"
QRCODE_FILE = "qrcode.png"
ID_LOG_CLIENTES = 1474620768498356224
ID_LOG_PAGAMENTOS = 1474620691050660020

# =========================
# FUNÇÕES DE ARQUIVO
# =========================

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_planos(data):
    with open(PLANOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# =========================
# VERIFICAÇÃO AUTOMÁTICA DE PLANOS
# =========================

async def enviar_dm_temp(usuario, embed, duracao=86400, view=None):
    try:
        msg = await usuario.send(embed=embed, view=view)
        await asyncio.sleep(duracao)
        await msg.delete()
    except:
        pass

async def verificar_planos():
    await bot.wait_until_ready()
    while not bot.is_closed():
        planos = load_planos()
        agora = time.time()
        alterado = False

        for guild_id, plano in planos.items():
            if plano.get("status") != "ativo":
                continue

            tempo_restante = plano.get("expira_em", 0) - agora
            comprador_id = plano.get("comprador_id")
            if not comprador_id:
                continue

            try:
                usuario = await bot.fetch_user(comprador_id)
            except:
                continue

            # Aviso 3 dias
            if 0 < tempo_restante <= 3 * 86400 and not plano.get("avisado_3dias", False):
                embed = discord.Embed(
                    title="⚠️ Seu plano está quase vencendo",
                    description=f"Faltam 3 dias para o vencimento do seu bot.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Servidor", value=f"ID: {guild_id}", inline=False)
                embed.add_field(name="Renove para evitar bloqueio.", value="Evite que seu sistema pare automaticamente.", inline=False)
                await enviar_dm_temp(usuario, embed, duracao=86400)
                plano["avisado_3dias"] = True
                alterado = True

            # Plano vencido
            if tempo_restante <= 0 and not plano.get("avisado_vencido", False):
                embed = discord.Embed(
                    title="❌ Plano Expirado",
                    description=f"Seu plano do servidor ID {guild_id} venceu.\nEscaneie o QR Code para renovar.",
                    color=discord.Color.red()
                )
                if os.path.exists(QRCODE_FILE):
                    file = discord.File(QRCODE_FILE, filename="qrcode.png")
                    embed.set_image(url="attachment://qrcode.png")
                    await enviar_dm_temp(usuario, embed, duracao=86400)
                else:
                    await enviar_dm_temp(usuario, embed, duracao=86400)

                plano["avisado_vencido"] = True
                plano["status"] = "encerrado"
                alterado = True

        if alterado:
            save_planos(planos)
        await asyncio.sleep(3600)

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    print(f"🔥 BOT ONLINE 🔥 | {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ {len(synced)} comandos sincronizados GLOBALMENTE")
    bot.loop.create_task(verificar_planos())

# Log de novo cliente
@bot.event
async def on_guild_join(guild):
    canal = bot.get_channel(ID_LOG_CLIENTES)
    if canal:
        embed = discord.Embed(
            title="🆕 Novo Cliente",
            color=discord.Color.green()
        )
        embed.add_field(name="Servidor", value=guild.name, inline=False)
        embed.add_field(name="ID Servidor", value=guild.id, inline=False)
        dono = guild.owner
        embed.add_field(name="Dono/Cliente", value=f"{dono} ({dono.id})", inline=False)
        await canal.send(embed=embed)

# =========================
# INICIALIZAÇÃO DOS COGS
# =========================

async def main():
    async with bot:
        # Carrega cogs
        await bot.load_extension("cogs.whitelist")
        print("✅ Cog whitelist carregado")
        await bot.load_extension("cogs.controle_financeiro")
        print("✅ Cog controle_financeiro carregado")
        await bot.start(TOKEN)

asyncio.run(main())