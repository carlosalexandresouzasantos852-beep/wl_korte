import discord
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio
import time
import os

CONFIG = "config.json"
PLANOS_FILE = "planos.json"

# ------------------------------
# UTILIDADES
# ------------------------------

def load_config():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_planos():
    if not os.path.exists(PLANOS_FILE):
        return {}
    with open(PLANOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def plano_ativo(guild_id):
    planos = load_planos()
    guild_id = str(guild_id)

    if guild_id not in planos:
        return False

    plano = planos[guild_id]

    if plano.get("status") != "ativo":
        return False

    if time.time() > plano.get("expira_em", 0):
        return False

    return True

# ------------------------------
# MODAL WHITELIST
# ------------------------------

class WLModal(Modal, title="📋 Whitelist"):
    nome = TextInput(label="Nome RP")
    idrp = TextInput(label="ID RP")
    recrutador = TextInput(label="Quem recrutou")

    async def on_submit(self, interaction: discord.Interaction):

        cfg = load_config()
        guild = interaction.guild
        categoria = guild.get_channel(cfg.get("categoria"))

        if not categoria:
            await interaction.response.send_message(
                "❌ Categoria não configurada.",
                ephemeral=True
            )
            return

        canal = await guild.create_text_channel(
            name=f"wl-{interaction.user.name}".lower(),
            category=categoria
        )

        embed = discord.Embed(
            title="📋 Nova Whitelist",
            color=discord.Color.orange()
        )
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Nome RP", value=self.nome.value, inline=True)
        embed.add_field(name="ID RP", value=self.idrp.value, inline=True)
        embed.add_field(name="Recrutador", value=self.recrutador.value, inline=False)

        await canal.send(
            embed=embed,
            view=WLView(interaction.user, self.nome.value, self.idrp.value)
        )

        await interaction.response.send_message(
            "✅ Whitelist enviada!",
            ephemeral=True
        )

# ------------------------------
# VIEW APROVAR / RECUSAR
# ------------------------------

class WLView(View):
    def __init__(self, user, nome, idrp):
        super().__init__(timeout=None)
        self.user = user
        self.nome = nome
        self.idrp = idrp

    def staff_check(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild

    async def deletar_msg(self, msg, tempo):
        await asyncio.sleep(tempo)
        try:
            await msg.delete()
        except:
            pass

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):

        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        cfg = load_config()
        aceitos_canal = interaction.guild.get_channel(cfg.get("aceitos"))

        embed = discord.Embed(
            title="✅ Whitelist Aprovada",
            color=discord.Color.green()
        )
        embed.add_field(name="Usuário", value=self.user.mention, inline=False)
        embed.add_field(name="Nome RP", value=self.nome, inline=True)
        embed.add_field(name="ID RP", value=self.idrp, inline=True)
        embed.add_field(name="Aprovado por", value=interaction.user.mention, inline=False)

        try:
            await self.user.edit(nick=f"{cfg['tag']} {self.nome} | {self.idrp}")
        except:
            if aceitos_canal:
                await aceitos_canal.send(
                    f"⚠️ Não foi possível alterar o nickname de {self.user.mention}."
                )

        if aceitos_canal:
            msg = await aceitos_canal.send(embed=embed)
            asyncio.create_task(self.deletar_msg(msg, 86400))

        await interaction.response.defer()
        await interaction.message.delete()
        await asyncio.sleep(1)

        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: Button):

        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        cfg = load_config()
        recusados_canal = interaction.guild.get_channel(cfg.get("recusados"))

        embed = discord.Embed(
            title="❌ Whitelist Recusada",
            color=discord.Color.red()
        )
        embed.add_field(name="Usuário", value=self.user.mention, inline=False)
        embed.add_field(name="Nome RP", value=self.nome, inline=True)
        embed.add_field(name="ID RP", value=self.idrp, inline=True)
        embed.add_field(name="Recusado por", value=interaction.user.mention, inline=False)

        if recusados_canal:
            msg = await recusados_canal.send(embed=embed)
            asyncio.create_task(self.deletar_msg(msg, 36000))

        await interaction.response.defer()
        await interaction.message.delete()
        await asyncio.sleep(1)

        try:
            await interaction.channel.delete()
        except:
            pass

# ------------------------------
# VIEW DO PAINEL
# ------------------------------

class PainelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Iniciar Whitelist", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):

        # 🔒 VERIFICAÇÃO FINANCEIRA
        if not plano_ativo(interaction.guild.id):

            await interaction.response.send_message(
                "❌ O plano mensal deste bot expirou.\n\n"
                "Entre em contato com o responsável para renovar.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(WLModal())