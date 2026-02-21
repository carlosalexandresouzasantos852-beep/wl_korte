import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
import time

# ------------------------------
# CONFIGURAÇÃO DO BOT
# ------------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN não encontrado no ambiente")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# ARQUIVOS E IDS
# ------------------------------
PLANOS_FILE = "planos.json"
QRCODE_FILE = "qrcode.png"
ID_LOG_CLIENTES = 1474620768498356224
ID_LOG_PAGAMENTOS = 1474620691050660020

# ------------------------------
# IMPORT DE VIEWS
# ------------------------------
from cogs.whitelist import ConfirmarPagamentoView

# ------------------------------
# FUNÇÕES DE ARQUIVO
# ------------------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ------------------------------
# LOOP DE VERIFICAÇÃO DE PLANOS
# ------------------------------
@tasks.loop(seconds=3600)
async def verificar_planos():
    planos = load_json(PLANOS_FILE)
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

        # Aviso 3 dias antes
        if 0 < tempo_restante <= 3*86400 and not plano.get("avisado_3dias", False):
            try:
                embed = discord.Embed(
                    title="⚠️ Seu plano está quase vencendo",
                    description=f"Faltam 3 dias para o vencimento do seu bot.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Servidor", value=f"ID: {guild_id}", inline=False)
                embed.add_field(name="Renove para evitar bloqueio.", value="Evite que seu sistema pare automaticamente.", inline=False)
                await usuario.send(embed=embed)
                plano["avisado_3dias"] = True
                alterado = True
            except:
                pass

        # Plano vencido
        if tempo_restante <= 0 and not plano.get("avisado_vencido", False):
            try:
                embed = discord.Embed(
                    title="❌ Plano Expirado",
                    description=f"O plano do servidor ID {guild_id} venceu.",
                    color=discord.Color.red()
                )
                embed.add_field(name="💰 Renovação - 30 dias", value="Escaneie o QR Code abaixo para renovar.", inline=False)

                # QR Code opcional
                file = discord.File(QRCODE_FILE, filename="qrcode.png") if os.path.exists(QRCODE_FILE) else None
                view = ConfirmarPagamentoView(usuario)

                await usuario.send(embed=embed, file=file, view=view)

                plano["avisado_vencido"] = True
                plano["status"] = "encerrado"
                alterado = True
            except:
                pass

    if alterado:
        save_json(PLANOS_FILE, planos)

# ------------------------------
# EVENTOS
# ------------------------------
@bot.event
async def on_ready():
    print(f"🔥 BOT ONLINE 🔥 | {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ {len(synced)} comandos sincronizados GLOBALMENTE")
    verificar_planos.start()

# ------------------------------
# INICIALIZAÇÃO DOS COGS
# ------------------------------
async def main():
    async with bot:
        await bot.load_extension("cogs.whitelist")
        print("✅ Cog whitelist carregado")
        await bot.load_extension("cogs.controle_financeiro")
        print("✅ Cog controle_financeiro carregado")
        await bot.start(TOKEN)

asyncio.run(main())