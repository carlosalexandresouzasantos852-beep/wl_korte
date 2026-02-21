import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import time
import os

PLANOS_FILE = "planos.json"

ID_LOG_CLIENTES = 1474620768498356224
ID_LOG_PAGAMENTOS = 1474620691050660020


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

    def __init__(self, guild_id, bot):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)
        self.bot = bot

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

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            # fallback se a interação expirar
            msg = await interaction.followup.send(embed=embed, view=self)
            await asyncio.sleep(1)
            await msg.delete()

    async def enviar_dm_cliente(self, guild, mensagem):
        try:
            owner = guild.owner
            if owner:
                await owner.send(mensagem)
        except:
            pass

    async def log_pagamento(self, titulo, guild, comprador_id, valor):
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed = discord.Embed(
                title=titulo,
                color=discord.Color.green() if "Ativado" in titulo else discord.Color.blurple
            )
            embed.add_field(name="Servidor", value=f"{guild.name}", inline=False)
            embed.add_field(name="ID Servidor", value=guild.id, inline=False)
            embed.add_field(name="Cliente", value=f"{guild.owner} ({guild.owner.id})", inline=False)
            embed.add_field(name="Valor", value=valor, inline=False)
            await canal.send(embed=embed)

    @discord.ui.button(label="Ativar 30 Dias", style=discord.ButtonStyle.green)
    async def ativar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        planos[self.guild_id] = {
            "status": "ativo",
            "expira_em": time.time() + (30 * 86400),
            "comprador_id": int(self.guild_id),  # para referência
            "avisado_3dias": False,
            "avisado_vencido": False
        }
        save_planos(planos)

        guild = interaction.guild
        await self.enviar_dm_cliente(guild, f"✅ Seu plano foi ATIVADO por 30 dias!\nServidor: {guild.name}")
        await self.log_pagamento("💰 Plano Ativado", guild, guild.owner.id, "R$ 29,90")
        await self.atualizar_status(interaction)

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
                "comprador_id": int(self.guild_id),
                "avisado_3dias": False,
                "avisado_vencido": False
            }
        save_planos(planos)
        guild = interaction.guild
        await self.enviar_dm_cliente(guild, f"🔄 Seu plano foi RENOVADO por +30 dias!\nServidor: {guild.name}")
        await self.log_pagamento("💰 Plano Renovado", guild, guild.owner.id, "R$ 29,90")
        await self.atualizar_status(interaction)

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
        guild = interaction.guild
        await self.log_pagamento("❌ Plano Encerrado", guild, guild.owner.id, "R$ 29,90")
        await self.atualizar_status(interaction)


# =========================
# COG
# =========================

class ControleFinanceiro(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.SEU_ID = 851409989762416681

    @commands.command()
    async def controlefinanceiro(self, ctx, guild_id: str):
        if ctx.author.id != self.SEU_ID:
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
        view = PainelFinanceiro(guild_id, self.bot)
        await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Sempre envia log, mesmo se já tiver log antigo
        canal = self.bot.get_channel(ID_LOG_CLIENTES)
        if canal:
            embed = discord.Embed(
                title="🆕 Novo Cliente",
                color=discord.Color.green()
            )
            embed.add_field(name="Servidor", value=guild.name, inline=False)
            embed.add_field(name="ID Servidor", value=guild.id, inline=False)
            embed.add_field(name="Dono / Cliente", value=f"{guild.owner} ({guild.owner.id})", inline=False)
            await canal.send(embed=embed)


# =========================
# SETUP
# =========================

async def setup(bot):
    await bot.add_cog(ControleFinanceiro(bot))