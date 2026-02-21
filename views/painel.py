import discord
from discord.ui import View, Button
from discord.ext import commands
import time
import json
import os
from cogs.whitelist import WhitelistModal, ConfirmarPagamentoView, plano_ativo, QRCODE_FILE, PLANOS_FILE, ID_LOG_PAGAMENTOS

CONFIG_FILE = "config.json"

# ------------------------------
# UTILIDADES
# ------------------------------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------------------------
# VIEW DO PAINEL UNIFICADO
# ------------------------------

class PainelUnificadoView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📋 Iniciar Whitelist", style=discord.ButtonStyle.green)
    async def iniciar_whitelist(self, interaction: discord.Interaction, button: Button):
        if not plano_ativo(interaction.guild.id):
            planos = load_json(PLANOS_FILE)
            comprador_id = planos.get(str(interaction.guild.id), {}).get("comprador_id")
            if comprador_id:
                cliente = await self.bot.fetch_user(comprador_id)
                embed = discord.Embed(
                    title="❌ Plano Vencido",
                    description=f"O plano do servidor **{interaction.guild.name}** venceu.\nRenove pelo QR Code.",
                    color=discord.Color.red()
                )
                view = ConfirmarPagamentoView(cliente)
                if os.path.exists(QRCODE_FILE):
                    file = discord.File(QRCODE_FILE, filename="qrcode.png")
                    embed.set_image(url="attachment://qrcode.png")
                    await cliente.send(embed=embed, file=file, view=view)
                else:
                    await cliente.send(embed=embed, view=view)
            await interaction.response.send_message(
                "❌ O plano deste servidor está vencido. O responsável foi notificado por DM.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(WhitelistModal())

    @discord.ui.button(label="💰 Status Plano", style=discord.ButtonStyle.blurple)
    async def status_plano(self, interaction: discord.Interaction, button: Button):
        planos = load_json(PLANOS_FILE)
        guild_id = str(interaction.guild.id)
        if guild_id not in planos:
            status = "❌ Nenhum plano ativo"
        else:
            plano = planos[guild_id]
            if plano["status"] != "ativo":
                status = "❌ Plano encerrado"
            else:
                restante = int(plano["expira_em"] - time.time())
                dias = restante // 86400
                horas = (restante % 86400) // 3600
                status = f"✅ Ativo\n⏳ Expira em: {dias} dias e {horas} horas"
        embed = discord.Embed(
            title="📊 Status do Plano",
            description=status,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------
# COG PARA ENVIAR O PAINEL
# ------------------------------

class Painel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def painel(self, ctx):
        """Envia o painel unificado para o servidor"""
        embed = discord.Embed(
            title="📋 PAINEL UNIFICADO",
            description="💰 Controle Financeiro e Whitelist\nClique nos botões abaixo para iniciar.",
            color=discord.Color.orange()
        )
        view = PainelUnificadoView(self.bot)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Painel(bot))