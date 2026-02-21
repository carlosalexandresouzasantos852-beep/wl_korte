import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os
import asyncio
import time

CONFIG_FILE = "config.json"
PLANOS_FILE = "planos.json"
QRCODE_FILE = "qrcode.png"
ID_LOG_PAGAMENTOS = 1474620691050660020

# ------------------------------
# UTILIDADES
# ------------------------------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def plano_ativo(guild_id):
    planos = load_json(PLANOS_FILE)
    guild_id = str(guild_id)
    plano = planos.get(guild_id)
    if not plano or plano.get("status") != "ativo":
        return False
    if time.time() > plano.get("expira_em", 0):
        return False
    return True

# ------------------------------
# MODAL WHITELIST
# ------------------------------

class WhitelistModal(Modal, title="📋 Solicitação de Whitelist"):
    nome_rp = TextInput(label="👤 Nome RP", placeholder="Ex: João Silva")
    id_rp = TextInput(label="🆔 ID RP", placeholder="Ex: 1515")
    recrutador = TextInput(label="📝 Quem recrutou", placeholder="Ex: Recrutador")

    async def on_submit(self, interaction: discord.Interaction):
        config = load_json(CONFIG_FILE)
        guild = interaction.guild
        categoria = guild.get_channel(config.get("categoria"))

        if not categoria:
            await interaction.response.send_message("❌ Categoria não configurada.", ephemeral=True)
            return

        canal = await guild.create_text_channel(
            name=f"wl-{interaction.user.name}".lower(),
            category=categoria
        )

        embed = discord.Embed(
            title="📋 Nova Solicitação de Whitelist",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="📛 Nome RP", value=self.nome_rp.value, inline=False)
        embed.add_field(name="🆔 ID RP", value=self.id_rp.value, inline=False)
        embed.add_field(name="📝 Quem recrutou", value=self.recrutador.value, inline=False)

        await canal.send(embed=embed, view=WhitelistView(interaction.user, self.nome_rp.value, self.id_rp.value))
        await interaction.response.send_message("✅ Whitelist enviada para análise!", ephemeral=True)

# ------------------------------
# VIEW APROVAR / RECUSAR
# ------------------------------

class WhitelistView(View):
    def __init__(self, usuario, nome, idrp):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.nome = nome
        self.idrp = idrp

    def staff_check(self, interaction):
        return interaction.user.guild_permissions.manage_guild

    async def send_embed_temp(self, canal, titulo, descricao, duracao=86400):
        msg = await canal.send(embed=discord.Embed(title=titulo, description=descricao,
                                                    color=discord.Color.green() if "Aprovada" in titulo else discord.Color.red()))
        await asyncio.sleep(duracao)
        await msg.delete()

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        config = load_json(CONFIG_FILE)
        canal_aceitos = interaction.guild.get_channel(config.get("aceitos"))
        tag = config.get("tag")
        cargo_id = config.get("cargo")
        cargo_bot = interaction.guild.me.top_role

        try:
            if self.usuario.top_role < cargo_bot:
                await self.usuario.edit(nick=f"{tag} {self.nome} | {self.idrp}")
        except:
            pass

        if cargo_id:
            role = interaction.guild.get_role(cargo_id)
            if role:
                await self.usuario.add_roles(role)

        if canal_aceitos:
            descricao = (
                f"👤 Usuário: {self.usuario.mention}\n"
                f"📛 Nome RP: {self.nome}\n"
                f"🆔 ID: {self.idrp}\n"
                f"✅ Aprovado por: {interaction.user.mention}"
            )
            asyncio.create_task(self.send_embed_temp(canal_aceitos, "✅ Whitelist Aprovada", descricao, 86400))

        await interaction.response.defer()
        await interaction.message.delete()
        await asyncio.sleep(1)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        config = load_json(CONFIG_FILE)
        canal_recusados = interaction.guild.get_channel(config.get("recusados"))
        if canal_recusados:
            descricao = (
                f"👤 Usuário: {self.usuario.mention}\n"
                f"📛 Nome RP: {self.nome}\n"
                f"🆔 ID: {self.idrp}\n"
                f"❌ Recusado por: {interaction.user.mention}"
            )
            asyncio.create_task(self.send_embed_temp(canal_recusados, "❌ Whitelist Recusada", descricao, 86400))

        await interaction.response.defer()
        await interaction.message.delete()
        await asyncio.sleep(1)
        await interaction.channel.delete()

# ------------------------------
# BOTÃO CONFIRMAR PAGAMENTO
# ------------------------------

class ConfirmarPagamentoView(View):
    def __init__(self, cliente):
        super().__init__(timeout=86400)
        self.cliente = cliente

    @discord.ui.button(label="💳 Confirmar Pagamento", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.cliente.id:
            await interaction.response.send_message("❌ Apenas o cliente pode confirmar.", ephemeral=True)
            return

        await interaction.response.send_message("✅ Pagamento confirmado! Aguarde ativação manual.", ephemeral=True)

        # Log para você
        canal = interaction.client.get_channel(ID_LOG_PAGAMENTOS)
        if canal:
            embed_log = discord.Embed(
                title="💰 Pagamento Confirmado",
                description=f"Cliente {self.cliente} confirmou o pagamento.",
                color=discord.Color.green()
            )
            await canal.send(embed=embed_log)

        self.clear_items()
        await interaction.message.edit(view=self)

# ------------------------------
# VIEW DO PAINEL
# ------------------------------

class PainelView(View):
    def __init__(self, bot, gif_url=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.gif_url = gif_url

    @discord.ui.button(label="📋 Iniciar Whitelist", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):
        if not plano_ativo(interaction.guild.id):
            from cogs.whitelist import ConfirmarPagamentoView
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

# ------------------------------
# COG
# ------------------------------

class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config_wl", description="Configurar sistema de whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_wl(
        self, interaction: discord.Interaction,
        canal_painel: discord.TextChannel,
        categoria: discord.CategoryChannel,
        aceitos: discord.TextChannel,
        recusados: discord.TextChannel,
        cargo: discord.Role,
        tag: str
    ):
        data = {
            "painel": canal_painel.id,
            "categoria": categoria.id,
            "aceitos": aceitos.id,
            "recusados": recusados.id,
            "cargo": cargo.id,
            "tag": tag
        }
        save_json(CONFIG_FILE, data)
        await interaction.response.send_message("✅ Whitelist configurada!", ephemeral=True)

    @app_commands.command(name="painel_wl", description="Abrir painel de whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_wl(self, interaction: discord.Interaction, gif_url: str = None):
        config = load_json(CONFIG_FILE)
        canal = interaction.guild.get_channel(config.get("painel"))
        if not canal:
            await interaction.response.send_message("❌ Canal do painel inválido.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 PAINEL DE WHITELIST",
            description="📝 Clique no botão abaixo para iniciar.\n⏳ Aguarde análise.",
            color=discord.Color.orange()
        )
        if gif_url:
            embed.set_image(url=gif_url)
        await canal.send(embed=embed, view=PainelView(self.bot, gif_url))
        await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Whitelist(bot))