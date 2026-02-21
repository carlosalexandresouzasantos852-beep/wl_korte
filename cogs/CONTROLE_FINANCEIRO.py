import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import time
import os
import asyncio

PLANOS_FILE = "planos.json"

ID_LOG_CLIENTES = 1474620768498356224
ID_LOG_PAGAMENTOS = 1474620691050660020
QRCODE_PATH = "qrcode.png"

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
# VIEW DE CONFIRMAÇÃO DE PAGAMENTO
# =========================

class ConfirmarPagamento(View):
    def __init__(self, bot, guild_id, comprador_id):
        super().__init__(timeout=24*3600)  # 24h de duração
        self.bot = bot
        self.guild_id = guild_id
        self.comprador_id = comprador_id

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        # Log para você
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed = discord.Embed(
                title="💰 Pagamento Confirmado",
                color=discord.Color.green()
            )
            embed.add_field(name="Servidor", value=f"`{self.guild_id}`", inline=False)
            embed.add_field(name="Cliente", value=f"<@{self.comprador_id}> ({self.comprador_id})", inline=False)
            embed.add_field(name="Mensagem", value="O cliente confirmou o pagamento. Ative o plano manualmente.", inline=False)
            await canal.send(embed=embed)

        await interaction.message.delete()  # remove DM junto com botão
        self.stop()

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
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Ativar 30 Dias", style=discord.ButtonStyle.green)
    async def ativar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        planos[self.guild_id] = {
            "status": "ativo",
            "expira_em": time.time() + (30 * 86400),
            "comprador_id": planos.get(self.guild_id, {}).get("comprador_id", interaction.user.id),
            "avisado_3dias": False,
            "avisado_vencido": False
        }
        save_planos(planos)

        # DM pro cliente confirmando ativação
        comprador_id = planos[self.guild_id]["comprador_id"]
        try:
            usuario = await self.bot.fetch_user(comprador_id)
            await usuario.send(f"✅ Seu plano foi ATIVADO por 30 dias!\nServidor ID: `{self.guild_id}`")
        except:
            pass

        # Log pagamento
        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed = discord.Embed(title="💰 Plano Ativado", color=discord.Color.green)
            embed.add_field(name="Servidor ID", value=f"`{self.guild_id}`", inline=False)
            embed.add_field(name="Cliente", value=f"<@{comprador_id}> ({comprador_id})", inline=False)
            embed.add_field(name="Valor", value="R$ 29,90", inline=False)
            await canal.send(embed=embed)

        await self.atualizar_status(interaction)

    @discord.ui.button(label="Renovar +30 Dias", style=discord.ButtonStyle.blurple)
    async def renovar(self, interaction: discord.Interaction, button: Button):
        planos = load_planos()
        if self.guild_id in planos and planos[self.guild_id]["status"] == "ativo":
            planos[self.guild_id]["expira_em"] += (30 * 86400)
        else:
            planos[self.guild_id] = {
                "status": "ativo",
                "expira_em": time.time() + (30 * 86400),
                "comprador_id": planos.get(self.guild_id, {}).get("comprador_id", interaction.user.id),
                "avisado_3dias": False,
                "avisado_vencido": False
            }
        save_planos(planos)

        comprador_id = planos[self.guild_id]["comprador_id"]
        try:
            usuario = await self.bot.fetch_user(comprador_id)
            await usuario.send(f"🔄 Seu plano foi RENOVADO por +30 dias!\nServidor ID: `{self.guild_id}`")
        except:
            pass

        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed = discord.Embed(title="💰 Plano Renovado", color=discord.Color.blurple)
            embed.add_field(name="Servidor ID", value=f"`{self.guild_id}`", inline=False)
            embed.add_field(name="Cliente", value=f"<@{comprador_id}> ({comprador_id})", inline=False)
            embed.add_field(name="Valor", value="R$ 29,90", inline=False)
            await canal.send(embed=embed)

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

        canal = self.bot.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed = discord.Embed(title="❌ Plano Encerrado", color=discord.Color.red)
            embed.add_field(name="Servidor ID", value=f"`{self.guild_id}`", inline=False)
            embed.add_field(name="Encerrado por", value=f"{interaction.user} ({interaction.user.id})", inline=False)
            await canal.send(embed=embed)

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

    # LOG AUTOMÁTICO DE NOVO CLIENTE
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        canal = self.bot.get_channel(ID_LOG_CLIENTES)
        if canal:
            embed = discord.Embed(title="🆕 Novo Cliente", color=discord.Color.green)
            embed.add_field(name="Servidor", value=f"`{guild.name}`", inline=False)
            embed.add_field(name="ID Servidor", value=f"`{guild.id}`", inline=False)
            embed.add_field(name="Dono", value=f"{guild.owner} (`{guild.owner.id}`)", inline=False)
            await canal.send(embed=embed)

# =========================
# SETUP
# =========================

async def setup(bot):
    await bot.add_cog(ControleFinanceiro(bot))