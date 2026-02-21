import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio
import time
import os

CONFIG_FILE = "config.json"
PLANOS_FILE = "planos.json"

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

    if guild_id not in planos:
        return False

    plano = planos[guild_id]

    if plano.get("status") != "ativo":
        return False

    if time.time() > plano.get("expira_em", 0):
        return False

    return True

async def notificar_comprador(bot, guild):
    planos = load_json(PLANOS_FILE)
    guild_id = str(guild.id)

    if guild_id not in planos:
        return

    comprador_id = planos[guild_id].get("comprador_id")
    if not comprador_id:
        return

    try:
        comprador = await bot.fetch_user(comprador_id)

        if os.path.exists("qrcode.png"):
            await comprador.send(
                f"❌ O plano do servidor **{guild.name}** venceu.\n\n"
                f"Para reativar, realize o pagamento abaixo:",
                file=discord.File("qrcode.png")
            )
        else:
            await comprador.send(
                f"❌ O plano do servidor **{guild.name}** venceu.\n\n"
                f"Entre em contato para renovar."
            )
    except:
        pass

# ------------------------------
# MODAL DE WHITELIST
# ------------------------------

class WhitelistModal(Modal, title="📋 Solicitação de Whitelist"):

    nome_rp = TextInput(label="👤 Nome RP", placeholder="Ex: João Silva")
    id_rp = TextInput(label="🆔 ID RP", placeholder="Ex: 1515")
    recrutador = TextInput(label="📝 Quem recrutou", placeholder="Ex: Nome do recrutador")

    async def on_submit(self, interaction: discord.Interaction):

        config = load_json(CONFIG_FILE)
        guild = interaction.guild

        categoria_id = config.get("categoria")
        if not categoria_id:
            await interaction.response.send_message("❌ Categoria não configurada.", ephemeral=True)
            return

        categoria = guild.get_channel(categoria_id)
        if not categoria:
            await interaction.response.send_message("❌ Categoria não encontrada.", ephemeral=True)
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

        await canal.send(
            embed=embed,
            view=WhitelistView(interaction.user, self.nome_rp.value, self.id_rp.value)
        )

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

    async def send_embed_temp(self, canal, titulo, descricao, duracao):
        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=discord.Color.green() if "Aprovada" in titulo else discord.Color.red()
        )
        msg = await canal.send(embed=embed)
        await asyncio.sleep(duracao)
        await msg.delete()

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):

        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        config = load_json(CONFIG_FILE)

        canal_aceitos = interaction.guild.get_channel(config.get("aceitos"))
        cargo_id = config.get("cargo")
        tag = config.get("tag")
        cargo_bot = interaction.guild.me.top_role

        await interaction.response.send_message("✅ Aprovado!", ephemeral=True)

        try:
            if self.usuario.top_role < cargo_bot:
                await self.usuario.edit(nick=f"{tag} {self.nome} | {self.idrp}")
        except:
            pass

        try:
            if cargo_id:
                role = interaction.guild.get_role(cargo_id)
                if role:
                    await self.usuario.add_roles(role)
        except:
            pass

        if canal_aceitos:
            descricao = (
                f"👤 Usuário: {self.usuario.mention}\n"
                f"📛 Nome RP: {self.nome}\n"
                f"🆔 ID: {self.idrp}\n"
                f"✅ Aprovado por: {interaction.user.mention}"
            )
            asyncio.create_task(
                self.send_embed_temp(canal_aceitos, "✅ Whitelist Aprovada", descricao, 86400)
            )

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
            asyncio.create_task(
                self.send_embed_temp(canal_recusados, "❌ Whitelist Recusada", descricao, 36000)
            )

        await interaction.response.send_message("❌ Recusado!", ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()

# ------------------------------
# VIEW DO PAINEL COM BLOQUEIO FINANCEIRO
# ------------------------------

class PainelView(View):

    def __init__(self, bot, gif_url=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.gif_url = gif_url

    @discord.ui.button(label="📋 Iniciar Whitelist - TROPA DO TIO PATINHAS", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):

        if not plano_ativo(interaction.guild.id):

            await notificar_comprador(self.bot, interaction.guild)

            await interaction.response.send_message(
                "❌ O plano deste servidor está vencido.\n"
                "O responsável foi notificado por DM.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(WhitelistModal())

# ------------------------------
# COG PRINCIPAL
# ------------------------------

class Whitelist(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config_wl", description="Configurar o sistema de whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_wl(
        self,
        interaction: discord.Interaction,
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

    @app_commands.command(name="painel_wl", description="Abrir o painel de whitelist")
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

# ------------------------------
# SETUP
# ------------------------------

async def setup(bot):
    await bot.add_cog(Whitelist(bot))