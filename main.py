import discord
from discord.ext import commands
import asyncio
import os
import json
import time

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN não encontrado no ambiente")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

PLANOS_FILE = "planos.json"
QRCODE_PATH = "qrcode.png"  # imagem local do QR


# ==============================
# 📂 FUNÇÕES DE ARQUIVO
# ==============================

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_planos(data):
    with open(PLANOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ==============================
# 🔔 VERIFICAÇÃO AUTOMÁTICA
# ==============================

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

            # ======================
            # 📅 AVISO 3 DIAS
            # ======================

            if 0 < tempo_restante <= 3 * 86400:
                if not plano.get("avisado_3dias", False):
                    try:
                        embed = discord.Embed(
                            title="⚠️ Seu plano está quase vencendo",
                            description="Faltam 3 dias para o vencimento do seu bot.",
                            color=discord.Color.orange()
                        )

                        embed.add_field(
                            name="Servidor",
                            value=f"ID: {guild_id}",
                            inline=False
                        )

                        embed.add_field(
                            name="Renove para evitar bloqueio.",
                            value="Evite que seu sistema pare automaticamente.",
                            inline=False
                        )

                        await usuario.send(embed=embed)

                        plano["avisado_3dias"] = True
                        alterado = True

                    except:
                        pass

            # ======================
            # ❌ PLANO VENCIDO
            # ======================

            if tempo_restante <= 0:
                if not plano.get("avisado_vencido", False):
                    try:
                        embed = discord.Embed(
                            title="❌ Plano Expirado",
                            description="Seu plano mensal venceu.",
                            color=discord.Color.red()
                        )

                        embed.add_field(
                            name="💰 Renovação - 30 dias",
                            value="Valor: R$ 29,90\nEscaneie o QR Code abaixo para renovar.",
                            inline=False
                        )

                        if os.path.exists(QRCODE_PATH):
                            file = discord.File(QRCODE_PATH, filename="qrcode.png")
                            embed.set_image(url="attachment://qrcode.png")
                            await usuario.send(embed=embed, file=file)
                        else:
                            await usuario.send(embed=embed)

                        plano["avisado_vencido"] = True
                        plano["status"] = "encerrado"
                        alterado = True

                    except:
                        pass

        if alterado:
            save_planos(planos)

        await asyncio.sleep(3600)


# ==============================
# 🚀 EVENTOS
# ==============================

@bot.event
async def on_ready():
    print(f"🔥 BOT ONLINE 🔥 | {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ {len(synced)} comandos sincronizados GLOBALMENTE")

    bot.loop.create_task(verificar_planos())


# ==============================
# 🧠 INICIALIZAÇÃO
# ==============================

async def main():
    async with bot:
        await bot.load_extension("cogs.whitelist")
        print("✅ Cog whitelist carregado")

        await bot.load_extension("cogs.controle_financeiro")
        print("✅ Cog controle_financeiro carregado")

        await bot.start(TOKEN)


asyncio.run(main())