import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import time
import os

PLANOS_FILE = "planos.json"

# =========================
# UTILIDADES
# =========================

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_planos(data):
    with open(PLANOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def formatar_tempo(timestamp):
    restante = int(timestamp - time.time())

    if restante <= 0:
        return "Vencido"

    dias = restante // 86400
    horas = (restante % 86400) // 3600

    return f"{dias} dias e {horas} horas"


# =========================
# VIEW DO CONTROLE
# =========================

class PainelFinanceiro(View):

    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)

    async def atualizar_status(self, interaction):
        planos = load_planos()

        if self.guild_id not in planos:
            status = "❌ Nenhum plano ativo"
        else:
            plano = planos[self.guild_id]

            if plano["status"] != "ativo":
                status = "❌ Plano encerrado"
            else:
                status = f"✅ Ativo\n⏳ Expira em: {formatar_tempo(plano['expira_em'])}"

        embed = discord.Embed(
            title="📊 Controle Financeiro",
            description=f"Servidor ID: `{self.guild_id}`\n\n{status}",
            color=discord.Color.gold()
        )

        await interaction.response.edit_message(embed=embed, view=self)

    # =========================
    # BOTÃO ATIVAR
    # =========================

    @discord.ui.button(label="Ativar 30 Dias", style=discord.ButtonStyle.green)
    async def ativar(self, interaction: discord.Interaction, button: Button):

        planos = load_planos()

        planos[self.guild_id] = {
            "status": "ativo",
            "expira_em": time.time() + (30 * 86400),
            "comprador_id": interaction.user.id,
            "avisado_3dias": False,
            "avisado_vencido": False
        }

        save_planos(planos)

        await self.atualizar_status(interaction)

    # =========================
    # BOTÃO RENOVAR
    # =========================

    @discord.ui.button(label="Renovar +30 Dias", style=discord.ButtonStyle.blurple)
    async def renovar(self, interaction: discord.Interaction, button: Button):

        planos = load_planos()

        if self.guild_id in planos and planos[self.guild_id]["status"] == "ativo":
            planos[self.guild_id]["expira_em"] += (30 * 86400)
            planos[self.guild_id]["avisado_3dias"] = False
            planos[self.guild_id]["avisado_vencido"] = False
        else:
            planos[self.guild_id] = {
                "status": "ativo",
                "expira_em": time.time() + (30 * 86400),
                "comprador_id": interaction.user.id,
                "avisado_3dias": False,
                "avisado_vencido": False
            }

        save_planos(planos)

        await self.atualizar_status(interaction)

    # =========================
    # BOTÃO ENCERRAR
    # =========================

    @discord.ui.button(label="Encerrar Plano", style=discord.ButtonStyle.red)
    async def encerrar(self, interaction: discord.Interaction, button: Button):

        planos = load_planos()

        planos[self.guild_id] = {
            "status": "encerrado",
            "expira_em": 0,
            "comprador_id": planos.get(self.guild_id, {}).get("comprador_id"),
            "avisado_3dias": False,
            "avisado_vencido": False
        }

        save_planos(planos)

        await self.atualizar_status(interaction)


# =========================
# COMANDO
# =========================

def setup(bot: commands.Bot):

    SEU_ID = 123456789012345678  # 🔥 COLOQUE SEU ID AQUI

    @bot.command()
    async def controlefinanceiro(ctx, guild_id: str):

        if ctx.author.id != SEU_ID:
            return

        planos = load_planos()

        if guild_id not in planos:
            status = "❌ Nenhum plano ativo"
        else:
            plano = planos[guild_id]

            if plano["status"] != "ativo":
                status = "❌ Plano encerrado"
            else:
                status = f"✅ Ativo\n⏳ Expira em: {formatar_tempo(plano['expira_em'])}"

        embed = discord.Embed(
            title="📊 Controle Financeiro",
            description=f"Servidor ID: `{guild_id}`\n\n{status}",
            color=discord.Color.gold()
        )

        view = PainelFinanceiro(guild_id)

        await ctx.send(embed=embed, view=view)