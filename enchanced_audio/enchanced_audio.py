import asyncio
import contextlib
import math
import time
from pathlib import Path
from typing import List, MutableMapping, Optional, Union, Dict

import discord
import lavalink
from discord import app_commands
from red_commons.logging import getLogger

from redbot.core import commands, Config
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number

log = getLogger("red.cogs.EnhancedAudio")
_ = Translator("EnhancedAudio", Path(__file__))

class EnhancedAudioView(discord.ui.View):
    def __init__(self, cog, ctx, timeout=300):  # Aumentado para 5 minutos
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.message = None
        self.update_task = None
        
    async def start(self):
        """Inicia a view e a tarefa de atualização."""
        self.update_task = self.ctx.bot.loop.create_task(self.periodic_update())
        
    async def stop(self):
        """Para a view e a tarefa de atualização."""
        if self.update_task:
            self.update_task.cancel()
        await super().stop()
        
    async def periodic_update(self):
        """Atualiza o embed periodicamente."""
        try:
            while not self.ctx.bot.is_closed():
                await self.update_now_playing()
                await asyncio.sleep(10)  # Atualiza a cada 10 segundos
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Erro na atualização periódica: {e}")
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se o usuário que interage é o autor do comando ou um DJ."""
        if interaction.user.id == self.ctx.author.id:
            return True
        
        # Verifica se o usuário tem permissões de DJ
        if await self.cog.original_cog._can_instaskip(self.ctx, interaction.user):
            return True
            
        await interaction.response.send_message("Você não tem permissão para usar estes controles.", ephemeral=True)
        return False
    
    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def repeat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para alternar o modo repetição."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_repeat(self.ctx)
        
        # Atualiza a visualização
        guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
        if guild_data["repeat"]:
            button.style = discord.ButtonStyle.success
            await interaction.followup.send("🔄 Modo repetição ativado", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            await interaction.followup.send("🔄 Modo repetição desativado", ephemeral=True)
        
        await self.update_now_playing()
        
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para voltar para a música anterior."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        # Como o cog Audio não tem comando nativo para voltar, usamos o seek para o início
        # Em uma implementação mais avançada, poderia armazenar histórico de músicas
        await self.cog.original_cog.command_seek(self.ctx, seconds=0)
        await interaction.followup.send("⏮️ Voltando ao início da música atual", ephemeral=True)
        
        await self.update_now_playing()
        
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para parar a reprodução."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_stop(self.ctx)
        
        # Atualiza a mensagem após parar
        embed = discord.Embed(
            title="⏹️ Reprodução Interrompida",
            description="A reprodução de música foi interrompida.",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.followup.edit_message(message_id=self.message.id, embed=embed, view=None)
        self.stop()
        
    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para alternar entre play e pause."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        # Alterna entre play e pause
        if player.paused:
            await interaction.response.defer(ephemeral=True)
            await self.cog.original_cog.command_pause(self.ctx)
            button.emoji = "⏸️"
            await interaction.followup.send("▶️ Reprodução retomada", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)
            await self.cog.original_cog.command_pause(self.ctx)
            button.emoji = "▶️"
            await interaction.followup.send("⏸️ Reprodução pausada", ephemeral=True)
            
        await interaction.followup.edit_message(message_id=self.message.id, view=self)
            
        # Atualiza o último momento de atividade
        self.cog.last_activity[self.ctx.guild.id] = time.time()
   
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para pular a música atual."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        current_track = player.current
        await self.cog.original_cog.command_skip(self.ctx)
        
        # Atualiza o último momento de atividade
        self.cog.last_activity[self.ctx.guild.id] = time.time()
        
        # Cria um embed informativo
        if current_track:
            track_description = await self.cog.original_cog.get_track_description(
                current_track, 
                self.cog.original_cog.local_folder_current_path
            ) or "Desconhecido"
            
            embed = discord.Embed(
                title="⏭️ Música Pulada",
                description=f"**{track_description}**",
                color=0x3498db
            )
            
            # Se houver próxima música na fila
            if player.current:
                next_track = await self.cog.original_cog.get_track_description(
                    player.current, 
                    self.cog.original_cog.local_folder_current_path
                ) or "Desconhecido"
                embed.add_field(name="🎵 Agora Tocando", value=f"**{next_track}**", inline=False)
                
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Atualiza o embed após pular
        await self.update_now_playing()
    
    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para alternar o modo aleatório."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_shuffle(self.ctx)
        
        # Atualiza a visualização
        guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
        if guild_data["shuffle"]:
            button.style = discord.ButtonStyle.success
            await interaction.followup.send("🔀 Modo aleatório ativado", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            await interaction.followup.send("🔀 Modo aleatório desativado", ephemeral=True)
        
        await self.update_now_playing()
        
    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def volume_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para aumentar o volume."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        # Aumenta o volume em 10%
        current_volume = await self.cog.original_cog.config.guild(self.ctx.guild).volume()
        new_volume = min(150, current_volume + 10)
        await self.cog.original_cog.command_volume(self.ctx, vol=new_volume)
        
        await interaction.followup.send(f"🔊 Volume aumentado para {new_volume}%", ephemeral=True)
        await self.update_now_playing()
        
    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1)
    async def volume_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para diminuir o volume."""
        player = lavalink.get_player(self.ctx.guild.id)
        
        if not player.current:
            await interaction.response.send_message("Não há nada tocando atualmente.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        # Diminui o volume em 10%
        current_volume = await self.cog.original_cog.config.guild(self.ctx.guild).volume()
        new_volume = max(0, current_volume - 10)
        await self.cog.original_cog.command_volume(self.ctx, vol=new_volume)
        
        await interaction.followup.send(f"🔉 Volume diminuído para {new_volume}%", ephemeral=True)
        await self.update_now_playing()
    
    async def update_now_playing(self):
        """Atualiza o embed de reprodução atual."""
        if not self.message:
            return
            
        try:
            # Verifica se a mensagem ainda existe
            try:
                await self.message.channel.fetch_message(self.message.id)
            except discord.NotFound:
                # Se a mensagem não existe mais, para a tarefa de atualização
                if self.update_task:
                    self.update_task.cancel()
                return
                
            player = lavalink.get_player(self.ctx.guild.id)
            guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
            
            if not player.current:
                embed = discord.Embed(
                    title="🎵 Nada Tocando",
                    description="Não há música em reprodução no momento.",
                    color=0x3498db
                )
                await self.message.edit(embed=embed, view=self)
                return
                
            arrow = await self.cog.original_cog.draw_time(self.ctx)
            pos = self.cog.original_cog.format_time(player.position)
            
            if player.current.is_stream:
                dur = "LIVE"
                progress_bar = "🔴 TRANSMISSÃO AO VIVO"
            else:
                dur = self.cog.original_cog.format_time(player.current.length)
                # Cria uma barra de progresso personalizada
                progress = min(1.0, player.position / player.current.length) if player.current.length > 0 else 0
                bar_length = 20
                position = round(progress * bar_length)
                progress_bar = "▬" * position + "🔘" + "▬" * (bar_length - position - 1)
                
            song = await self.cog.original_cog.get_track_description(
                player.current, 
                self.cog.original_cog.local_folder_current_path
            ) or ""
            
            # Volume atual
            volume = await self.cog.original_cog.config.guild(self.ctx.guild).volume()
            
            embed = discord.Embed(
                title="🎵 Tocando Agora",
                description=f"**{song}**\n\n"
                            f"{progress_bar}\n"
                            f"`{pos}` / `{dur}`\n\n"
                            f"Solicitado por: **{player.current.requester}**\n"
                            f"Volume: `{volume}%`",
                color=0x3498db
            )
            
            if guild_data["thumbnail"] and player.current and player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)
                
            # Adiciona informações sobre a fila
            if player.queue:
                próxima = await self.cog.original_cog.get_track_description(
                    player.queue[0], 
                    self.cog.original_cog.local_folder_current_path
                ) or "Desconhecida"
                embed.add_field(
                    name="📋 Próxima na Fila", 
                    value=f"**{próxima}**\n+ {len(player.queue) - 1} música(s) na fila", 
                    inline=False
                )
                
            # Status
            status = []
            if guild_data["repeat"]:
                status.append("🔄 Repetição: Ativada")
            if guild_data["shuffle"]:
                status.append("🔀 Aleatório: Ativado")
            if guild_data["auto_play"]:
                status.append("⏭️ Auto-Play: Ativado")
                
            if status:
                embed.add_field(name="⚙️ Status", value="\n".join(status), inline=True)
                
            # Atualiza a mensagem e renova o timeout da view
            await self.message.edit(embed=embed, view=self)
            self.timeout = 300  # Renova o timeout para 5 minutos
            
        except discord.NotFound:
            # Se a mensagem não existe mais, para a tarefa de atualização
            if self.update_task:
                self.update_task.cancel()
        except Exception as e:
            log.error(f"Erro ao atualizar o embed: {e}")
            # Se ocorrer um erro, verifica se a mensagem ainda existe
            try:
                await self.message.channel.fetch_message(self.message.id)
            except discord.NotFound:
                # Se a mensagem não existe mais, para a tarefa de atualização
                if self.update_task:
                    self.update_task.cancel()

class EnhancedQueueView(discord.ui.View):
    def __init__(self, cog, ctx, pages, timeout=300):  # Aumentado para 5 minutos
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0
        self.message = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se o usuário que interage é o autor do comando."""
        if interaction.user.id == self.ctx.author.id:
            return True
            
        await interaction.response.send_message("Apenas o autor do comando pode usar estes botões.", ephemeral=True)
        return False
    
    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ir para a página anterior da fila."""
        if self.current_page == 0:
            self.current_page = len(self.pages) - 1
        else:
            self.current_page -= 1
            
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        self.timeout = 300  # Renova o timeout para 5 minutos
    
    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ir para a próxima página da fila."""
        if self.current_page == len(self.pages) - 1:
            self.current_page = 0
        else:
            self.current_page += 1
            
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        self.timeout = 300  # Renova o timeout para 5 minutos
    
    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary)
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para embaralhar a fila."""
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_shuffle(self.ctx)
        
        # Regenerar as páginas após embaralhar
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.queue:
            await interaction.followup.send("A fila está vazia após embaralhar.", ephemeral=True)
            return
            
        self.pages = await self.cog.create_queue_pages(self.ctx)
        self.current_page = 0
        await interaction.followup.send("🔀 Fila embaralhada com sucesso!", ephemeral=True)
        await interaction.followup.edit_message(message_id=self.message.id, embed=self.pages[0], view=self)
        self.timeout = 300  # Renova o timeout para 5 minutos
    
    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger)
    async def close_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Fechar o menu de fila."""
        await interaction.response.defer(ephemeral=True)
        await interaction.message.delete()
        await interaction.followup.send("Menu de fila fechado", ephemeral=True)
        self.stop()

class EnhancedAudio(commands.Cog):
    """Versão aprimorada do cog Audio com interface melhorada."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=13371337, force_registration=True)
        self.original_cog = None
        self.last_activity = {}  # Armazena o último momento de atividade por guild
        self.last_messages = {}  # Armazena a última mensagem enviada por guild
        self.background_task = None
        
    async def initialize(self):
        """Inicializa o cog encontrando a referência ao cog Audio original."""
        self.original_cog = self.bot.get_cog("Audio")
        if not self.original_cog:
            log.error("Não foi possível encontrar o cog Audio original. EnhancedAudio não funcionará corretamente.")
            return
            
        # Inicia a tarefa de verificação de inatividade
        self.background_task = self.bot.loop.create_task(self.check_inactivity())
            
    async def cog_unload(self):
        """Limpa recursos quando o cog é descarregado."""
        if self.background_task:
            self.background_task.cancel()
            
    async def check_inactivity(self):
        """Verifica a inatividade de reprodução."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                current_time = time.time()
                guilds_to_clean = []
                
                for guild_id, last_time in self.last_activity.items():
                    if current_time - last_time > 60:  # 60 segundos = 1 minuto
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            player = lavalink.get_player(guild_id)
                            if player and not player.current:
                                guilds_to_clean.append(guild_id)
                
                for guild_id in guilds_to_clean:
                    # Remove a última mensagem
                    last_message = self.last_messages.get(guild_id)
                    if last_message:
                        try:
                            await last_message.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                        
                    # Limpa as entradas do dicionário
                    self.last_activity.pop(guild_id, None)
                    self.last_messages.pop(guild_id, None)
                    
            except Exception as e:
                log.error(f"Erro na verificação de inatividade: {e}")
                
            await asyncio.sleep(15)  # Verifica a cada 15 segundos
            
    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        """Atualiza tokens da API quando eles são alterados."""
        if service_name == "spotify":
            if self.original_cog:
                await self.original_cog.api_interface.spotify_api.update_token(api_tokens)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Só intercepta mensagens do bot, em texto, com embed, e do Audio
        if not message.guild:
            return
        if message.author.id != self.bot.user.id:
            return
        if not message.embeds:
            return

        try:
            embed = message.embeds[0]
            # Filtra pelo título do embed
            if embed.title and embed.title.lower() in ["now playing", "tocando agora", "track enqueued", "track added"]:
                # Verifica se já existe um embed ativo para este servidor
                last_message = self.last_messages.get(message.guild.id)
                if last_message:
                    try:
                        # Tenta buscar a mensagem para ver se ainda existe
                        await last_message.channel.fetch_message(last_message.id)
                        # Se a mensagem existe, apenas atualiza ela
                        ctx = await self.bot.get_context(message)
                        view = EnhancedAudioView(self, ctx)
                        view.message = last_message
                        
                        # Atualiza a mensagem existente
                        await view.start()
                        await view.update_now_playing()
                        
                        # Apaga a mensagem original
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return
                    except discord.NotFound:
                        # Se a mensagem não existe mais, continua com o fluxo normal
                        pass

                # Apaga a mensagem original
                try:
                    await message.delete()
                except Exception:
                    pass

                # Envia o embed bonito com botões
                ctx = await self.bot.get_context(message)
                view = EnhancedAudioView(self, ctx)
                
                # Envia diretamente o embed em vez da mensagem de carregamento
                new_embed = discord.Embed(
                    title="🎵 Tocando Agora",
                    description="Preparando informações da música...",
                    color=0x3498db
                )
                new_msg = await message.channel.send(embed=new_embed, view=view)
                
                view.message = new_msg
                self.last_messages[ctx.guild.id] = new_msg
                self.last_activity[ctx.guild.id] = time.time()
                
                # Inicia a tarefa de atualização periódica
                await view.start()
                await view.update_now_playing()
                
            # Intercepta mensagens de status do cog Audio original
            elif message.content and any(status in message.content.lower() for status in [
                "track paused", "track resumed", "track skipped", "track enqueued", "track added",
                "música pausada", "música retomada", "música pulada", "música adicionada"
            ]):
                # Apaga a mensagem original
                try:
                    await message.delete()
                except Exception:
                    pass
        except Exception as e:
            log.error(f"Erro ao processar mensagem: {e}")

    async def create_queue_pages(self, ctx):
        """Cria páginas para o comando de fila."""
        player = lavalink.get_player(ctx.guild.id)
        items_per_page = 10
        pages = []
        queue_list = player.queue
        
        if not queue_list:
            embed = discord.Embed(
                title="📋 Fila de Reprodução",
                description="A fila está vazia. Adicione músicas com o comando `play`.",
                color=0x3498db
            )
            
            if player.current:
                current = await self.original_cog.get_track_description(
                    player.current, 
                    self.original_cog.local_folder_current_path
                ) or "Desconhecido"
                embed.add_field(name="🎵 Tocando Agora", value=f"**{current}**", inline=False)
                
            pages.append(embed)
            return pages
            
        # Cria as páginas
        for i in range(0, len(queue_list), items_per_page):
            queue_chunk = queue_list[i:i + items_per_page]
            
            embed = discord.Embed(
                title="📋 Fila de Reprodução",
                color=0x3498db
            )
            
            if i == 0 and player.current:
                current = await self.original_cog.get_track_description(
                    player.current, 
                    self.original_cog.local_folder_current_path
                ) or "Desconhecido"
                embed.add_field(name="🎵 Tocando Agora", value=f"**{current}**", inline=False)
            
            queue_text = ""
            for index, track in enumerate(queue_chunk, start=i + 1):
                track_description = await self.original_cog.get_track_description(
                    track, 
                    self.original_cog.local_folder_current_path
                ) or "Desconhecido"
                queue_text += f"**{index}.** {track_description}\n"
                
            if queue_text:
                embed.description = queue_text
                
            embed.set_footer(text=f"Página {i//items_per_page + 1}/{math.ceil(len(queue_list)/items_per_page)} • Total: {len(queue_list)} músicas")
            pages.append(embed)
            
        return pages
        
    @commands.command(name="eplay")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_eplay(self, ctx: commands.Context, *, query: str):
        """Reproduz a música ou pesquisa especificada com uma interface aprimorada."""
        if not self.original_cog:
            await ctx.send("O cog Audio original não foi encontrado. Este comando não funcionará.")
            return
            
        try:
            # Verifica se já existe um embed ativo para este servidor
            last_message = self.last_messages.get(ctx.guild.id)
            if last_message:
                try:
                    # Tenta buscar a mensagem para ver se ainda existe
                    await last_message.channel.fetch_message(last_message.id)
                    # Se a mensagem existe, apenas atualiza ela
                    view = EnhancedAudioView(self, ctx)
                    view.message = last_message
                    
                    # Atualiza a mensagem existente
                    await view.start()
                    await view.update_now_playing()
                    
                    # Chama o comando play original
                    await self.original_cog.command_play(ctx, query=query)
                    return
                except discord.NotFound:
                    # Se a mensagem não existe mais, continua com o fluxo normal
                    pass

            # Cria uma mensagem inicial com um embed bonito
            embed = discord.Embed(
                title="🔍 Buscando",
                description=f"`{query}`",
                color=0x3498db
            )
            embed.set_footer(text="Aguarde enquanto procuramos a música...")
            message = await ctx.send(embed=embed)
            
            # Registra a atividade
            self.last_activity[ctx.guild.id] = time.time()
            self.last_messages[ctx.guild.id] = message
            
            # Chama o comando play original
            await self.original_cog.command_play(ctx, query=query)
            
            # Verifica se a música foi adicionada
            player = lavalink.get_player(ctx.guild.id)
            
            if player.current:
                view = EnhancedAudioView(self, ctx)
                view.message = message
                
                # Atualiza a mensagem com controles
                await view.start()
                await view.update_now_playing()
                await message.edit(view=view)
            else:
                # Se falhou, atualiza a mensagem com erro
                embed.title = "❌ Falha na Reprodução"
                embed.description = "Não foi possível reproduzir a música solicitada."
                embed.color = 0xe74c3c
                await message.edit(embed=embed)
        except Exception as e:
            log.error(f"Erro no comando eplay: {e}")
            try:
                await ctx.send("❌ Ocorreu um erro ao tentar reproduzir a música. Por favor, tente novamente.")
            except Exception:
                pass

    @commands.command(name="enow")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_enow(self, ctx: commands.Context):
        """Mostra a música atual com controles interativos."""
        if not self.original_cog:
            await ctx.send("O cog Audio original não foi encontrado. Este comando não funcionará.")
            return
            
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="🎵 Nada Tocando",
                    description="Não há música em reprodução no momento.",
                    color=0x3498db
                )
                await ctx.send(embed=embed)
                return
                
            player = lavalink.get_player(ctx.guild.id)
            view = EnhancedAudioView(self, ctx)
            
            guild_data = await self.original_cog.config.guild(ctx.guild).all()
            shuffle_button = [x for x in view.children if x.emoji and x.emoji.name == "🔀"][0]
            repeat_button = [x for x in view.children if x.emoji and x.emoji.name == "🔄"][0]
            
            if guild_data["shuffle"]:
                shuffle_button.style = discord.ButtonStyle.success
            if guild_data["repeat"]:
                repeat_button.style = discord.ButtonStyle.success
                
            # Ajusta o botão de play/pause
            pause_button = [x for x in view.children if x.emoji and (x.emoji.name == "⏯️" or x.emoji.name == "▶️" or x.emoji.name == "⏸️")][0]
            pause_button.emoji = "⏸️" if not player.paused else "▶️"
            
            # Cria diretamente um embed inicial bonito
            initial_embed = discord.Embed(
                title="🎵 Tocando Agora",
                description="Preparando informações da música...",
                color=0x3498db
            )
            
            message = await ctx.send(embed=initial_embed, view=view)
            view.message = message
            
            # Registra a atividade e a mensagem
            self.last_activity[ctx.guild.id] = time.time()
            self.last_messages[ctx.guild.id] = message
            
            # Inicia a tarefa de atualização periódica
            await view.start()
            await view.update_now_playing()
        except Exception as e:
            log.error(f"Erro no comando enow: {e}")
            try:
                await ctx.send("❌ Ocorreu um erro ao tentar mostrar a música atual. Por favor, tente novamente.")
            except Exception:
                pass

    @commands.command(name="equeue")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_equeue(self, ctx: commands.Context):
        """Mostra a fila de reprodução com uma interface aprimorada."""
        if not self.original_cog:
            await ctx.send("O cog Audio original não foi encontrado. Este comando não funcionará.")
            return
            
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="📋 Fila de Reprodução",
                    description="Não há música em reprodução no momento.",
                    color=0x3498db
                )
                await ctx.send(embed=embed)
                return
                
            pages = await self.create_queue_pages(ctx)
            view = EnhancedQueueView(self, ctx, pages)
            
            message = await ctx.send(embed=pages[0], view=view)
            view.message = message
            
            # Atualiza a última atividade
            self.last_activity[ctx.guild.id] = time.time()
        except Exception as e:
            log.error(f"Erro no comando equeue: {e}")
            try:
                await ctx.send("❌ Ocorreu um erro ao tentar mostrar a fila. Por favor, tente novamente.")
            except Exception:
                pass

    @commands.command(name="eskip")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_eskip(self, ctx: commands.Context):
        """Pula a música atual com uma interface aprimorada."""
        if not self.original_cog:
            await ctx.send("O cog Audio original não foi encontrado. Este comando não funcionará.")
            return
            
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="🎵 Nada Tocando",
                    description="Não há música em reprodução no momento.",
                    color=0x3498db
                )
                await ctx.send(embed=embed)
                return
                
            # Registra a música atual antes de pular
            player = lavalink.get_player(ctx.guild.id)
            current_track = player.current
            
            # Atualiza a última atividade
            self.last_activity[ctx.guild.id] = time.time()
            
            # Chama o comando skip original
            await self.original_cog.command_skip(ctx)
            
            # Cria um embed informativo
            if current_track:
                track_description = await self.original_cog.get_track_description(
                    current_track, 
                    self.original_cog.local_folder_current_path
                ) or "Desconhecido"
                
                embed = discord.Embed(
                    title="⏭️ Música Pulada",
                    description=f"**{track_description}**",
                    color=0x3498db
                )
                
                # Se houver próxima música na fila
                if player.current:
                    next_track = await self.original_cog.get_track_description(
                        player.current, 
                        self.original_cog.local_folder_current_path
                    ) or "Desconhecido"
                    embed.add_field(name="🎵 Agora Tocando", value=f"**{next_track}**", inline=False)
                    
                await ctx.send(embed=embed)
        except Exception as e:
            log.error(f"Erro no comando eskip: {e}")
            try:
                await ctx.send("❌ Ocorreu um erro ao tentar pular a música. Por favor, tente novamente.")
            except Exception:
                pass

async def setup(bot):
    cog = EnhancedAudio(bot)
    await bot.add_cog(cog)
    await cog.initialize()