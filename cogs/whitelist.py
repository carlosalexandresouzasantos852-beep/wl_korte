import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio

CONFIG_FILE = "config.json"

# ------------------------------
# Funções de salvar/carregar config
# ------------------------------
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ------------------------------
# Modal de Whitelist
# ------------------------------
class WhitelistModal(Modal, title="📋 Solicitação de Whitelist"):
    nome_rp = TextInput(label="👤 Nome RP", placeholder="Ex: João Silva")
    id_rp = TextInput(label="🆔 ID RP", placeholder="Ex: 1515")
    recrutador = TextInput(label="📝 Quem recrutou", placeholder="Ex: Nome do recrutador")

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild = interaction.guild

        categoria_id = config.get("categoria")
        if not categoria_id:
            await interaction.response.send_message("❌ Categoria não configurada.", ephemeral=True)
            return

        categoria = guild.get_channel(categoria_id)
        if not categoria:
            await interaction.response.send_message("❌ Categoria não encontrada.", ephemeral=True)
            return

        # Cria o canal temporário de análise
        canal = await guild.create_text_channel(
            name=f"wl-{interaction.user.name}".lower(),
            category=categoria
        )

        # Embed com informações do usuário
        embed = discord.Embed(
            title="📋 Nova Solicitação de Whitelist",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="📛 Nome RP", value=self.nome_rp.value, inline=False)
        embed.add_field(name="🆔 ID RP", value=self.id_rp.value, inline=False)
        embed.add_field(name="📝 Quem recrutou", value=self.recrutador.value, inline=False)

        await canal.send(embed=embed, view=WhitelistView(interaction.user, self.nome_rp.value, self.id_rp.value, interaction.user))

        # Mensagem para o usuário que enviou a WL, some em 3 segundos
        await interaction.response.send_message("✅ Whitelist enviada para análise da staff KORTE!", ephemeral=True)
        asyncio.create_task(self.delete_ephemeral_message(interaction))

    async def delete_ephemeral_message(self, interaction):
        await asyncio.sleep(3)
        try:
            await interaction.delete_original_response()
        except:
            pass

# ------------------------------
# View de Aprovar/Recusar
# ------------------------------
class WhitelistView(View):
    def __init__(self, usuario, nome, idrp, solicitante):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.nome = nome
        self.idrp = idrp
        self.solicitante = solicitante

    def staff_check(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild

    async def send_embed_temporary(self, canal, titulo, descricao, duracao):
        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=discord.Color.green() if "aprovada" in titulo.lower() else discord.Color.red()
        )
        embed.set_footer(text="Whitelist System - KORTE")
        msg = await canal.send(embed=embed)
        await asyncio.sleep(duracao)
        await msg.delete()

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
            return

        config = load_config()
        canal_aceitos = interaction.guild.get_channel(config.get("aceitos"))
        cargo_config = config.get("cargo")
        tag = config.get("tag")
        cargo_bot = interaction.guild.me.top_role

        # Responde interação primeiro para evitar "interação falhou"
        await interaction.response.send_message("✅ Aprovado!", ephemeral=True)

        nick_msg = ""
        cargo_msg = ""

        # Tenta alterar o nickname
        try:
            if self.usuario.top_role < cargo_bot:
                await self.usuario.edit(nick=f"{tag} {self.nome} | {self.idrp}")
            else:
                nick_msg = f"❌ Não foi possível alterar o nickname de {self.usuario.mention}, cargo muito alto.\n"
        except:
            nick_msg = f"❌ Não foi possível alterar o nickname de {self.usuario.mention},VC É O DONO KKK.\n"

        # Tenta adicionar o cargo configurado
        try:
            if cargo_config:
                role = interaction.guild.get_role(cargo_config)
                if role:
                    await self.usuario.add_roles(role)
        except:
            cargo_msg = f"❌ Não foi possível adicionar o cargo configurado a {self.usuario.mention}.\n"

        # Embed detalhado no canal de aceitos
        if canal_aceitos:
            descricao = (
                f"👤 Usuário:\n{self.usuario.mention}\n\n"
                f"📛 Nome RP:\n{self.nome}\n\n"
                f"🆔 ID:\n{self.idrp}\n\n"
                f"✅ Aprovado por:\n{interaction.user.mention}\n\n"
                f"{nick_msg}{cargo_msg}"
            )
            asyncio.create_task(self.send_embed_temporary(canal_aceitos, "✅ Whitelist Aprovada", descricao, duracao=86400))

        # Aguarda 1 segundo e deleta o canal temporário
        await asyncio.sleep(1)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
            return

        config = load_config()
        canal_recusados = interaction.guild.get_channel(config.get("recusados"))

        if canal_recusados:
            descricao = (
                f"👤 Usuário:\n{self.usuario.mention}\n\n"
                f"📛 Nome RP:\n{self.nome}\n\n"
                f"🆔 ID:\n{self.idrp}\n\n"
                f"❌ Recusado por:\n{interaction.user.mention}"
            )
            asyncio.create_task(self.send_embed_temporary(canal_recusados, "❌ Whitelist Recusada", descricao, duracao=36000))

        await interaction.response.send_message("❌ Recusado!", ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()

# ------------------------------
# View do Painel
# ------------------------------
class PainelView(View):
    def __init__(self, gif_url=None):
        super().__init__(timeout=None)
        self.gif_url = gif_url or "https://cdn.discordapp.com/attachments/1266573285236408363/1453240164351610931/ezgif.com-video-to-gif-converter.gif"

    @discord.ui.button(label="📋 Iniciar Whitelist - KORTE", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WhitelistModal())

# ------------------------------
# Cog principal
# ------------------------------
class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="config_wl",
        description="Configurar o sistema de whitelist"
    )
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
        save_config(data)
        await interaction.response.send_message("✅ **Whitelist configurada com sucesso!**", ephemeral=True)

    @app_commands.command(
        name="painel_wl",
        description="Abrir o painel de whitelist"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_wl(self, interaction: discord.Interaction, gif_url: str = None):
        config = load_config()
        canal = interaction.guild.get_channel(config.get("painel"))
        if not canal:
            await interaction.response.send_message("❌ Canal do painel inválido.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 PAINEL DE WHITELIST - KORTE",
            description="📝 Clique no botão abaixo para iniciar sua whitelist.\n⚠️ Responda corretamente.\n⏳ Aguarde a análise.",
            color=discord.Color.orange()
        )
        embed.set_image(url=gif_url or "https://cdn.discordapp.com/attachments/1266573285236408363/1453240164351610931/ezgif.com-video-to-gif-converter.gif")

        await canal.send(embed=embed, view=PainelView(gif_url))
        await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)

# ------------------------------
# Setup
# ------------------------------
async def setup(bot):
    await bot.add_cog(Whitelist(bot))