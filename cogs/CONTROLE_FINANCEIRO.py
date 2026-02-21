import discord
from discord.ext import commands
from discord.ui import View, Button
import time
import json
import os
import asyncio

PLANOS_FILE = "planos.json"
ID_LOG_CLIENTES = 1474620768498356224
ID_LOG_PAGAMENTOS = 1474620691050660020

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_planos(data):
    with open(PLANOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def plano_ativo(guild_id):
    planos = load_planos()
    guild_id = str(guild_id)
    plano = planos.get(guild_id)
    if not plano or plano.get("status") != "ativo":
        return False
    if time.time() > plano.get("expira_em", 0):
        return False
    return True

def formatar_tempo(timestamp):
    restante = int(timestamp - time.time())
    if restante <= 0:
        return "Vencido"
    dias = restante // 86400
    horas = (restante % 86400) // 3600
    return f"{dias} dias e {horas} horas"

async def enviar_dm_temp(usuario, embed, duracao=86400, view=None):
    try:
        msg = await usuario.send(embed=embed, view=view)
        await asyncio.sleep(duracao)
        await msg.delete()
    except:
        pass

# ------------------------------
# VIEW FINANCEIRO
# ------------------------------

class PainelFinanceiro(View):
    def __init__(self, guild_id, bot):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)
        self.bot = bot

    async def atualizar_status(self, interaction):
        planos = load_planos()
        plano = planos.get(self.guild_id)
        if not plano or plano.get("status") != "ativo":
            status = "❌ Nenhum plano ativo"
        else:
            status = f"✅ Ativo\n⏳ Expira em: {formatar_tempo(plano['expira_em'])}"
        embed = discord.Embed(
            title="📊 Controle Financeiro",
            description=f"Servidor ID: `{self.guild_id}`\n\n{status}",
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # ---------- BOTÃO ATIVAR 30 DIAS ----------
    @discord.ui.button(label="Ativar 30 Dias", style=discord.ButtonStyle.green)
    async def ativar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        guild = interaction.guild
        comprador_id = guild.owner.id

        planos[self.guild_id] = {
            "status": "ativo",
            "expira_em": time.time() + 30*86400,
            "comprador_id": comprador_id,
            "avisado_3dias": False,
            "avisado_vencido": False
        }
        save_planos(planos)

        # DM para o cliente
        try:
            cliente = await self.bot.fetch_user(comprador_id)
            embed_cliente = discord.Embed(
                title="✅ Plano Ativado",
                description=f"Seu plano do servidor **{guild.name}** foi ativado por 30 dias.",
                color=discord.Color.green()
            )
            await enviar_dm_temp(cliente, embed_cliente, duracao=86400)
        except:
            pass

        # Log para você
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed_log = discord.Embed(title="💰 Plano Ativado", color=discord.Color.green)
            embed_log.add_field(name="Servidor", value=guild.name, inline=False)
            embed_log.add_field(name="Cliente", value=f"{guild.owner} ({comprador_id})", inline=False)
            embed_log.add_field(name="Valor", value="R$ 29,90", inline=False)
            await canal.send(embed=embed_log)

        await self.atualizar_status(interaction)

    # ---------- BOTÃO RENOVAR 30 DIAS ----------
    @discord.ui.button(label="Renovar +30 Dias", style=discord.ButtonStyle.blurple)
    async def renovar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        guild = interaction.guild
        comprador_id = guild.owner.id

        if self.guild_id in planos and planos[self.guild_id]["status"] == "ativo":
            planos[self.guild_id]["expira_em"] += 30*86400
        else:
            planos[self.guild_id] = {
                "status": "ativo",
                "expira_em": time.time() + 30*86400,
                "comprador_id": comprador_id,
                "avisado_3dias": False,
                "avisado_vencido": False
            }
        save_planos(planos)

        # DM para o cliente
        try:
            cliente = await self.bot.fetch_user(comprador_id)
            embed_cliente = discord.Embed(
                title="🔄 Plano Renovado",
                description=f"Seu plano do servidor **{guild.name}** foi renovado por +30 dias.",
                color=discord.Color.blurple
            )
            await enviar_dm_temp(cliente, embed_cliente, duracao=86400)
        except:
            pass

        # Log
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed_log = discord.Embed(title="💰 Plano Renovado", color=discord.Color.blurple)
            embed_log.add_field(name="Servidor", value=guild.name, inline=False)
            embed_log.add_field(name="Cliente", value=f"{guild.owner} ({comprador_id})", inline=False)
            embed_log.add_field(name="Valor", value="R$ 29,90", inline=False)
            await canal.send(embed=embed_log)

        await self.atualizar_status(interaction)

    # ---------- BOTÃO ENCERRAR ----------
    @discord.ui.button(label="Encerrar Plano", style=discord.ButtonStyle.red)
    async def encerrar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        guild = interaction.guild
        comprador_id = planos.get(self.guild_id, {}).get("comprador_id")

        planos[self.guild_id] = {
            "status": "encerrado",
            "expira_em": 0,
            "comprador_id": comprador_id,
            "avisado_3dias": False,
            "avisado_vencido": False
        }
        save_planos(planos)

        # Log
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed_log = discord.Embed(title="❌ Plano Encerrado", color=discord.Color.red)
            embed_log.add_field(name="Servidor", value=guild.name, inline=False)
            embed_log.add_field(name="Encerrado por", value=f"{interaction.user} ({interaction.user.id})", inline=False)
            await canal.send(embed=embed_log)

        await self.atualizar_status(interaction)

# ------------------------------
# COG
# ------------------------------

class ControleFinanceiro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SEU_ID = 851409989762416681  # seu ID

    @commands.command()
    async def controlefinanceiro(self, ctx, guild_id: str):
        if ctx.author.id != self.SEU_ID:
            return
        planos = load_planos()
        plano = planos.get(guild_id)
        status = "❌ Nenhum plano ativo" if not plano else (
            "❌ Plano encerrado" if plano.get("status") != "ativo" else f"✅ Ativo\n⏳ Expira em: {formatar_tempo(plano['expira_em'])}"
        )
        embed = discord.Embed(title="📊 Controle Financeiro", description=f"Servidor ID: `{guild_id}`\n\n{status}", color=discord.Color.gold())
        view = PainelFinanceiro(guild_id, self.bot)
        await ctx.send(embed=embed, view=view)

    # Log de novo cliente
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        planos = load_planos()
        if str(guild.id) in planos:
            return  # evita duplicação
        canal = self.bot.get_channel(ID_LOG_CLIENTES)
        if canal:
            embed = discord.Embed(title="🆕 Novo Cliente", color=discord.Color.green)
            embed.add_field(name="Servidor", value=guild.name, inline=False)
            embed.add_field(name="ID Servidor", value=guild.id, inline=False)
            dono = guild.owner
            embed.add_field(name="Dono/Cliente", value=f"{dono} ({dono.id})", inline=False)
            await canal.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ControleFinanceiro(bot))