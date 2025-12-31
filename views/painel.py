import discord
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio

CONFIG = "config.json"

def load():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

class WLModal(Modal, title="📋 Whitelist"):

    nome = TextInput(label="👤 Nome RP")

    idrp = TextInput(label="🆔 ID RP")

    recrutador = TextInput(label="📝 Quem recrutou")

    async def on_submit(self, interaction: discord.Interaction):
        cfg = load()
        guild = interaction.guild
        categoria = guild.get_channel(cfg.get("categoria"))
        if not categoria:
            await interaction.response.send_message(
                "❌ Categoria não configurada.", ephemeral=True
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
        embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="📋 Nome RP", value=self.nome.value, inline=True)
        embed.add_field(name="🆔 ID RP", value=self.idrp.value, inline=True)
        embed.add_field(name="👤 Recrutador", value=self.recrutador.value, inline=False)

        await canal.send(embed=embed, view=WLView(interaction.user, self.nome.value, self.idrp.value))

        # Mensagem enviada sumindo em 5s
        msg = await interaction.response.send_message(
            "✅ Whitelist enviada!", ephemeral=True
        )
        await asyncio.sleep(5)
        try:
            await interaction.delete_original_response()
        except:
            pass

class WLView(View):
    def __init__(self, user, nome, idrp):
        super().__init__(timeout=None)
        self.user = user
        self.nome = nome
        self.idrp = idrp

    def staff_check(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        cfg = load()
        aceitos_canal = interaction.guild.get_channel(cfg.get("aceitos"))
        aprovado_embed = discord.Embed(
            title="✅ Whitelist Aprovada",
            color=discord.Color.green()
        )
        aprovado_embed.add_field(name="👤 Usuário", value=self.user.mention, inline=False)

        aprovado_embed.add_field(name="📋 Nome RP", value=self.nome, inline=True)

        aprovado_embed.add_field(name="🆔 ID RP", value=self.idrp, inline=True)

        aprovado_embed.add_field(name="👤 Aprovado por", value=interaction.user.mention, inline=False)

        try:
            await self.user.edit(nick=f"{cfg['tag']} {self.nome} | {self.idrp}")
        except:
            if aceitos_canal:
                await aceitos_canal.send(
                    f"⚠️ Não foi possível alterar seu nome {self.user.mention} (vc é o dono kkk)."
                )

        if aceitos_canal:
            msg = await aceitos_canal.send(embed=aprovado_embed)
            # Deleta após 24h
            asyncio.create_task(self.deletar_msg(msg, 86400))

        await interaction.message.delete()
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: Button):
        if not self.staff_check(interaction):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        cfg = load()
        recusados_canal = interaction.guild.get_channel(cfg.get("recusados"))
        recusado_embed = discord.Embed(
            title="❌ Whitelist Recusada",
            color=discord.Color.red()
        )
        recusado_embed.add_field(name="Usuário", value=self.user.mention, inline=False)
        recusado_embed.add_field(name="Nome RP", value=self.nome, inline=True)
        recusado_embed.add_field(name="ID RP", value=self.idrp, inline=True)
        recusado_embed.add_field(name="Recusado por", value=interaction.user.mention, inline=False)

        if recusados_canal:
            msg = await recusados_canal.send(embed=recusado_embed)
            # Deleta após 10h
            asyncio.create_task(self.deletar_msg(msg, 36000))

        await interaction.message.delete()
        try:
            await interaction.channel.delete()
        except:
            pass

    async def deletar_msg(self, msg, tempo):
        await asyncio.sleep(tempo)
        try:
            await msg.delete()
        except:
            pass

class PainelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Iniciar Whitelist-KORTE", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WLModal())