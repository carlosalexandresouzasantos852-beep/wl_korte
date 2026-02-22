import discord
from discord.ui import View, Button
from cogs.whitelist import WLModal, ConfirmarPagamentoView
import json
import os
import time

PLANOS_FILE = "planos.json"
QRCODE_FILE = "qrcode.png"

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_planos(planos):
    with open(PLANOS_FILE, "w", encoding="utf-8") as f:
        json.dump(planos, f, indent=4)

def plano_ativo(guild_id):
    planos = load_planos()
    guild_id = str(guild_id)
    if guild_id not in planos:
        return False
    plano = planos[guild_id]
    return plano.get("status") == "ativo" and time.time() < plano.get("expira_em", 0)

class PainelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📋 Iniciar Whitelist", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        planos = load_planos()
        guild_id = str(guild.id)
        dono = guild.owner

        # 🔒 Verifica plano ativo
        if not plano_ativo(guild.id):
            # Notifica apenas o dono do servidor
            embed = discord.Embed(
                title="❌ Plano Vencido",
                description=f"O plano do servidor **{guild.name}** está vencido.\nEscaneie o QR Code abaixo para renovar.",
                color=discord.Color.red()
            )
            view = ConfirmarPagamentoView(dono)
            file = None
            if os.path.exists(QRCODE_FILE):
                file = discord.File(QRCODE_FILE, filename="qrcode.png")
                embed.set_image(url="attachment://qrcode.png")

            await dono.send(embed=embed, file=file, view=view)
            await interaction.response.send_message(
                "❌ O plano deste servidor está vencido. O responsável foi notificado por DM.",
                ephemeral=True
            )
            return

        # Plano ativo → abre modal da whitelist
        await interaction.response.send_modal(WLModal())