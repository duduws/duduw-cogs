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
    def __init__(self, cog, ctx, timeout=300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.message = None
        self.update_task = None

    async def start(self):
        self.update_task = self.ctx.bot.loop.create_task(self.periodic_update())

    async def stop(self):
        if self.update_task:
            self.update_task.cancel()
        await super().stop()

    async def periodic_update(self):
        try:
            while not self.ctx.bot.is_closed():
                await self.update_now_playing()
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Error in periodic update: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.ctx.author.id:
            return True
        if await self.cog.original_cog._can_instaskip(self.ctx, interaction.user):
            return True
        await interaction.response.send_message(
            "You do not have permission to use these controls.", ephemeral=True
        )
        return False

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def repeat_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_repeat(self.ctx)
        guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
        if guild_data["repeat"]:
            button.style = discord.ButtonStyle.success
            await interaction.followup.send("🔄 Repeat mode enabled", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            await interaction.followup.send("🔄 Repeat mode disabled", ephemeral=True)
        await self.update_now_playing()

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary, row=0)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_seek(self.ctx, seconds=0)
        await interaction.followup.send(
            "⏮️ Restarted the current track.", ephemeral=True
        )
        await self.update_now_playing()

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Nothing is currently playing.", ephemeral=True
                )
            return
        await self.cog.delete_audio_cog_embeds(self.ctx)
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        await self.cog.original_cog.command_stop(self.ctx)
        embed = discord.Embed(
            title="⏹️ Playback Stopped",
            description="Music playback has been stopped.",
            color=0xE74C3C,
        )
        if not interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.followup.edit_message(
            message_id=self.message.id, embed=embed, view=None
        )
        await self.stop()

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def play_pause_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Nothing is currently playing.", ephemeral=True
                )
            return
        await self.cog.delete_audio_cog_embeds(self.ctx)
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        if player.paused:
            await self.cog.original_cog.command_pause(self.ctx)
            button.emoji = "⏸️"
            if not interaction.response.is_done():
                await interaction.followup.send("▶️ Playback resumed", ephemeral=True)
        else:
            await self.cog.original_cog.command_pause(self.ctx)
            button.emoji = "▶️"
            if not interaction.response.is_done():
                await interaction.followup.send("⏸️ Playback paused", ephemeral=True)
        await interaction.followup.edit_message(message_id=self.message.id, view=self)
        self.cog.last_activity[self.ctx.guild.id] = time.time()

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=0)
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        current_track = player.current
        await self.cog.original_cog.command_skip(self.ctx)
        self.cog.last_activity[self.ctx.guild.id] = time.time()
        if current_track:
            track_description = (
                await self.cog.original_cog.get_track_description(
                    current_track, self.cog.original_cog.local_folder_current_path
                )
                or "Unknown"
            )
            embed = discord.Embed(
                title="⏭️ Track Skipped",
                description=f"**{track_description}**",
                color=0x3498DB,
            )
            if player.current:
                next_track = (
                    await self.cog.original_cog.get_track_description(
                        player.current, self.cog.original_cog.local_folder_current_path
                    )
                    or "Unknown"
                )
                embed.add_field(
                    name="🎵 Now Playing", value=f"**{next_track}**", inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        await self.update_now_playing()

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_shuffle(self.ctx)
        guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
        if guild_data["shuffle"]:
            button.style = discord.ButtonStyle.success
            await interaction.followup.send("🔀 Shuffle mode enabled", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            await interaction.followup.send("🔀 Shuffle mode disabled", ephemeral=True)
        await self.update_now_playing()

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def volume_up_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await self.cog.delete_audio_cog_embeds(self.ctx)
        await interaction.response.defer(ephemeral=True)
        current_volume = await self.cog.original_cog.config.guild(
            self.ctx.guild
        ).volume()
        new_volume = min(150, current_volume + 10)
        await self.cog.original_cog.command_volume(self.ctx, vol=new_volume)
        await interaction.followup.send(
            f"🔊 Volume increased to {new_volume}%", ephemeral=True
        )
        await self.update_now_playing()

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1)
    async def volume_down_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.current:
            await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
            return
        await self.cog.delete_audio_cog_embeds(self.ctx)
        await interaction.response.defer(ephemeral=True)
        current_volume = await self.cog.original_cog.config.guild(
            self.ctx.guild
        ).volume()
        new_volume = max(0, current_volume - 10)
        await self.cog.original_cog.command_volume(self.ctx, vol=new_volume)
        await interaction.followup.send(
            f"🔉 Volume decreased to {new_volume}%", ephemeral=True
        )
        await self.update_now_playing()

    async def update_now_playing(self):
        if not self.message:
            return
        try:
            try:
                await self.message.channel.fetch_message(self.message.id)
            except discord.NotFound:
                if self.update_task:
                    self.update_task.cancel()
                return
            player = lavalink.get_player(self.ctx.guild.id)
            guild_data = await self.cog.original_cog.config.guild(self.ctx.guild).all()
            if not player.current:
                embed = discord.Embed(
                    title="🎵 Nothing Playing",
                    description="There is no music playing right now.",
                    color=0x3498DB,
                )
                await self.message.edit(embed=embed, view=self)
                return
            arrow = await self.cog.original_cog.draw_time(self.ctx)
            pos = self.cog.original_cog.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
                progress_bar = "🔴 LIVE STREAM"
            else:
                dur = self.cog.original_cog.format_time(player.current.length)
                progress = (
                    min(1.0, player.position / player.current.length)
                    if player.current.length > 0
                    else 0
                )
                bar_length = 20
                position = round(progress * bar_length)
                progress_bar = "▬" * position + "🔘" + "▬" * (bar_length - position - 1)
            song = (
                await self.cog.original_cog.get_track_description(
                    player.current, self.cog.original_cog.local_folder_current_path
                )
                or ""
            )
            volume = await self.cog.original_cog.config.guild(self.ctx.guild).volume()
            guild = self.ctx.guild
            author_icon = guild.icon.url if guild.icon else discord.Embed.Empty
            track_title = getattr(player.current, 'title', 'Unknown')
            track_uri = getattr(player.current, 'uri', None)
            track_thumbnail = getattr(player.current, 'thumbnail', None)
            requester = getattr(player.current, 'requester', None)
            requester_mention = None
            if requester:
                member = None
                try:
                    user_id = int(requester)
                    member = self.ctx.guild.get_member(user_id)
                except Exception:
                    member = discord.utils.find(lambda m: m.name == str(requester) or m.display_name == str(requester), self.ctx.guild.members)
                if member:
                    requester_mention = member.mention
                else:
                    requester_mention = f"{requester}"
            embed = discord.Embed(
                title="🎵 Now Playing",
                color=0x3498DB,
                description=f"[**{track_title}**]({track_uri})\n\n{progress_bar}\n`{pos}` / `{dur}`"
            )
            embed.set_author(name=guild.name, url="https://www.duduw.com.br", icon_url=author_icon)
            if track_thumbnail:
                embed.set_thumbnail(url=track_thumbnail)
            queue_count = len(player.queue)
            embed.add_field(name="Queue", value=f"{queue_count} tracks", inline=True)
            embed.add_field(name="Volume", value=f"{volume}%", inline=True)
            if requester_mention:
                embed.add_field(name="Requester", value=requester_mention, inline=True)
            status = []
            if guild_data["repeat"]:
                status.append("🔄 Repeat: Enabled")
            if guild_data["shuffle"]:
                status.append("🔀 Shuffle: Enabled")
            if guild_data["auto_play"]:
                status.append("⏭️ Auto-Play: Enabled")
            if status:
                embed.add_field(name="⚙️ Status", value="\n".join(status), inline=False)
            await self.message.edit(embed=embed, view=self)
            self.timeout = 300
        except discord.NotFound:
            if self.update_task:
                self.update_task.cancel()
        except Exception as e:
            log.error(f"Error updating embed: {e}")
            try:
                await self.message.channel.fetch_message(self.message.id)
            except discord.NotFound:
                if self.update_task:
                    self.update_task.cancel()


class EnhancedQueueView(discord.ui.View):
    def __init__(self, cog, ctx, pages, timeout=300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "Only the command author can use these buttons.", ephemeral=True
        )
        return False

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page == 0:
            self.current_page = len(self.pages) - 1
        else:
            self.current_page -= 1
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )
        self.timeout = 300

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page == len(self.pages) - 1:
            self.current_page = 0
        else:
            self.current_page += 1
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )
        self.timeout = 300

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary)
    async def shuffle_queue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        await self.cog.original_cog.command_shuffle(self.ctx)
        player = lavalink.get_player(self.ctx.guild.id)
        if not player.queue:
            await interaction.followup.send(
                "Queue is empty after shuffling.", ephemeral=True
            )
            return
        self.pages = await self.cog.create_queue_pages(self.ctx)
        self.current_page = 0
        await interaction.followup.send("🔀 Queue shuffled!", ephemeral=True)
        await interaction.followup.edit_message(
            message_id=self.message.id, embed=self.pages[0], view=self
        )
        self.timeout = 300

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger)
    async def close_menu(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        await interaction.message.delete()
        await interaction.followup.send("Queue menu closed", ephemeral=True)
        self.stop()


class EnhancedAudio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=13371337, force_registration=True
        )
        self.original_cog = None
        self.last_activity = {}
        self.last_messages = {}
        self.inactivity_task = self.inactivity_check.start()
        self.bot.loop.create_task(self._find_original_cog())

    async def _find_original_cog(self):
        await self.bot.wait_until_ready()
        self.original_cog = self.bot.get_cog("Audio")
        if not self.original_cog:
            log.error(
                "Could not find the original Audio cog. EnhancedAudio will not work properly."
            )

    from discord.ext import tasks

    @tasks.loop(seconds=15)
    async def inactivity_check(self):
        current_time = time.time()
        for guild_id, last_time in list(self.last_activity.items()):
            if current_time - last_time > 60:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    player = lavalink.get_player(guild_id)
                    if player and not player.current:
                        if getattr(player, 'channel_id', None):
                            await player.disconnect()
                        last_message = self.last_messages.get(guild_id)
                        if last_message:
                            try:
                                await last_message.delete()
                            except (discord.NotFound, discord.Forbidden):
                                pass
                        self.last_activity.pop(guild_id, None)
                        self.last_messages.pop(guild_id, None)

    async def cog_unload(self):
        if self.inactivity_task:
            self.inactivity_task.cancel()

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "spotify":
            if self.original_cog:
                await self.original_cog.api_interface.spotify_api.update_token(
                    api_tokens
                )

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.id != self.bot.user.id:
            return
        if not message.embeds and not message.content:
            return
        try:
            if message.embeds:
                embed = message.embeds[0]
                if embed.title and embed.title.lower() in [
                    "now playing",
                    "tocando agora",
                    "track enqueued",
                    "track added",
                ]:
                    last_message = self.last_messages.get(message.guild.id)
                    if last_message:
                        try:
                            await last_message.channel.fetch_message(last_message.id)
                            ctx = await self.bot.get_context(message)
                            view = EnhancedAudioView(self, ctx)
                            view.message = last_message
                            await view.start()
                            await view.update_now_playing()
                            try:
                                await message.delete()
                            except Exception:
                                pass
                            return
                        except discord.NotFound:
                            pass
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    ctx = await self.bot.get_context(message)
                    view = EnhancedAudioView(self, ctx)
                    new_embed = discord.Embed(
                        title="🎵 Now Playing",
                        description="Loading track information...",
                        color=0x3498DB,
                    )
                    new_msg = await message.channel.send(embed=new_embed, view=view)
                    view.message = new_msg
                    self.last_messages[ctx.guild.id] = new_msg
                    self.last_activity[ctx.guild.id] = time.time()
                    await view.start()
                    await view.update_now_playing()
            elif message.content and any(
                status in message.content.lower()
                for status in [
                    "track paused",
                    "track resumed",
                    "track skipped",
                    "track enqueued",
                    "track added",
                    "música pausada",
                    "música retomada",
                    "música pulada",
                    "música adicionada",
                    "volume increased",
                    "volume decreased",
                ]
            ):
                try:
                    await message.delete()
                except Exception:
                    pass
        except Exception as e:
            log.error(f"Error processing message: {e}")

    async def create_queue_pages(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        items_per_page = 10
        pages = []
        queue_list = player.queue
        if not queue_list:
            embed = discord.Embed(
                title="📋 Queue",
                description="The queue is empty. Add songs with the `play` command.",
                color=0x3498DB,
            )
            if player.current:
                current = (
                    await self.original_cog.get_track_description(
                        player.current, self.original_cog.local_folder_current_path
                    )
                    or "Unknown"
                )
                embed.add_field(
                    name="🎵 Now Playing", value=f"**{current}**", inline=False
                )
            pages.append(embed)
            return pages
        for i in range(0, len(queue_list), items_per_page):
            queue_chunk = queue_list[i : i + items_per_page]
            embed = discord.Embed(title="📋 Queue", color=0x3498DB)
            if i == 0 and player.current:
                current = (
                    await self.original_cog.get_track_description(
                        player.current, self.original_cog.local_folder_current_path
                    )
                    or "Unknown"
                )
                embed.add_field(
                    name="🎵 Now Playing", value=f"**{current}**", inline=False
                )
            queue_text = ""
            for index, track in enumerate(queue_chunk, start=i + 1):
                track_description = (
                    await self.original_cog.get_track_description(
                        track, self.original_cog.local_folder_current_path
                    )
                    or "Unknown"
                )
                queue_text += f"**{index}.** {track_description}\n"
            if queue_text:
                embed.description = queue_text
            embed.set_footer(
                text=f"Page {i//items_per_page + 1}/{math.ceil(len(queue_list)/items_per_page)} • Total: {len(queue_list)} tracks"
            )
            pages.append(embed)
        return pages

    @commands.command(name="eplay")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_eplay(self, ctx: commands.Context, *, query: str):
        if not self.original_cog:
            await ctx.send(
                "The original Audio cog was not found. This command will not work."
            )
            return
        try:
            await self.original_cog.command_play(ctx, query=query)
            player = lavalink.get_player(ctx.guild.id)
            if player.current:
                last_message = self.last_messages.get(ctx.guild.id)
                view = EnhancedAudioView(self, ctx)
                if last_message:
                    try:
                        await last_message.channel.fetch_message(last_message.id)
                        view.message = last_message
                        await view.start()
                        await view.update_now_playing()
                        await last_message.edit(view=view)
                        return
                    except discord.NotFound:
                        pass
                recent_msgs = [m async for m in ctx.channel.history(limit=5) if m.author == ctx.me and m.embeds and m.embeds[0].title == "🎵 Now Playing"]
                if recent_msgs:
                    msg = recent_msgs[0]
                    view.message = msg
                    self.last_activity[ctx.guild.id] = time.time()
                    self.last_messages[ctx.guild.id] = msg
                    await view.start()
                    await view.update_now_playing()
                    await msg.edit(view=view)
                    return
                initial_embed = discord.Embed(
                    title="🎵 Now Playing",
                    description="Loading track information...",
                    color=0x3498DB,
                )
                message = await ctx.send(embed=initial_embed, view=view)
                view.message = message
                self.last_activity[ctx.guild.id] = time.time()
                self.last_messages[ctx.guild.id] = message
                await view.start()
                await view.update_now_playing()
            else:
                embed = discord.Embed(
                    title="❌ Playback Failed",
                    description="Could not play the requested track.",
                    color=0xE74C3C,
                )
                await ctx.send(embed=embed)
        except Exception as e:
            log.error(f"Error in eplay command: {e}")
            try:
                await ctx.send(
                    "❌ An error occurred while trying to play the track. Please try again."
                )
            except Exception:
                pass

    @commands.command(name="enow")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_enow(self, ctx: commands.Context):
        if not self.original_cog:
            await ctx.send(
                "The original Audio cog was not found. This command will not work."
            )
            return
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="🎵 Nothing Playing",
                    description="There is no music playing right now.",
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)
                return
            player = lavalink.get_player(ctx.guild.id)
            view = EnhancedAudioView(self, ctx)
            guild_data = await self.original_cog.config.guild(ctx.guild).all()
            shuffle_button = [
                x for x in view.children if x.emoji and x.emoji.name == "🔀"
            ][0]
            repeat_button = [
                x for x in view.children if x.emoji and x.emoji.name == "🔄"
            ][0]
            if guild_data["shuffle"]:
                shuffle_button.style = discord.ButtonStyle.success
            if guild_data["repeat"]:
                repeat_button.style = discord.ButtonStyle.success
            pause_button = [
                x
                for x in view.children
                if x.emoji
                and (
                    x.emoji.name == "⏯️" or x.emoji.name == "▶️" or x.emoji.name == "⏸️"
                )
            ][0]
            pause_button.emoji = "⏸️" if not player.paused else "▶️"
            initial_embed = discord.Embed(
                title="🎵 Now Playing",
                description="Loading track information...",
                color=0x3498DB,
            )
            message = await ctx.send(embed=initial_embed, view=view)
            view.message = message
            self.last_activity[ctx.guild.id] = time.time()
            self.last_messages[ctx.guild.id] = message
            await view.start()
            await view.update_now_playing()
        except Exception as e:
            log.error(f"Error in enow command: {e}")
            try:
                await ctx.send(
                    "❌ An error occurred while trying to show the current track. Please try again."
                )
            except Exception:
                pass

    @commands.command(name="equeue")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_equeue(self, ctx: commands.Context):
        if not self.original_cog:
            await ctx.send(
                "The original Audio cog was not found. This command will not work."
            )
            return
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="📋 Queue",
                    description="There is no music playing right now.",
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)
                return
            pages = await self.create_queue_pages(ctx)
            view = EnhancedQueueView(self, ctx, pages)
            message = await ctx.send(embed=pages[0], view=view)
            view.message = message
            self.last_activity[ctx.guild.id] = time.time()
        except Exception as e:
            log.error(f"Error in equeue command: {e}")
            try:
                await ctx.send(
                    "❌ An error occurred while trying to show the queue. Please try again."
                )
            except Exception:
                pass

    @commands.command(name="eskip")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_eskip(self, ctx: commands.Context):
        if not self.original_cog:
            await ctx.send(
                "The original Audio cog was not found. This command will not work."
            )
            return
        try:
            if not self.original_cog._player_check(ctx):
                embed = discord.Embed(
                    title="🎵 Nothing Playing",
                    description="There is no music playing right now.",
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)
                return
            player = lavalink.get_player(ctx.guild.id)
            current_track = player.current
            self.last_activity[ctx.guild.id] = time.time()
            await self.original_cog.command_skip(ctx)
            if current_track:
                track_description = (
                    await self.original_cog.get_track_description(
                        current_track, self.original_cog.local_folder_current_path
                    )
                    or "Unknown"
                )
                embed = discord.Embed(
                    title="⏭️ Track Skipped",
                    description=f"**{track_description}**",
                    color=0x3498DB,
                )
                if player.current:
                    next_track = (
                        await self.original_cog.get_track_description(
                            player.current, self.original_cog.local_folder_current_path
                        )
                        or "Unknown"
                    )
                    embed.add_field(
                        name="🎵 Now Playing", value=f"**{next_track}**", inline=False
                    )
                await ctx.send(embed=embed)
        except Exception as e:
            log.error(f"Error in eskip command: {e}")
            try:
                await ctx.send(
                    "❌ An error occurred while trying to skip the track. Please try again."
                )
            except Exception:
                pass

    # Slash commands
    @app_commands.command(name="play", description="Play a song or playlist")
    @app_commands.describe(query="Type a song name or URL")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.command_eplay(ctx, query=query)
        await interaction.followup.send("Track added to queue!", ephemeral=True)

    @app_commands.command(name="pause", description="Pause the current track")
    async def slash_pause(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.original_cog.command_pause(ctx)
        await interaction.followup.send("Track paused!", ephemeral=True)

    @app_commands.command(name="stop", description="Stop playback")
    async def slash_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.original_cog.command_stop(ctx)
        await interaction.followup.send("Playback stopped!", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current track")
    async def slash_skip(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.command_eskip(ctx)
        await interaction.followup.send("Track skipped!", ephemeral=True)

    @app_commands.command(name="queue", description="Show the queue")
    async def slash_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.command_equeue(ctx)
        await interaction.followup.send("Queue shown above!", ephemeral=True)

    @app_commands.command(name="repeat", description="Toggle repeat mode")
    async def slash_repeat(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.original_cog.command_repeat(ctx)
        await interaction.followup.send("Repeat toggled!", ephemeral=True)

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def slash_shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.original_cog.command_shuffle(ctx)
        await interaction.followup.send("Queue shuffled!", ephemeral=True)

    @app_commands.command(name="volume", description="Set the volume (0-150%)")
    @app_commands.describe(volume="New volume value between 1 and 150.")
    async def slash_volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 1, 150]):
        await interaction.response.defer(ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        await self.original_cog.command_volume(ctx, vol=volume)
        await interaction.followup.send(f"Volume set to {volume}%!", ephemeral=True)

    # Playlist group (exemplo simplificado)
    playlist = app_commands.Group(name="playlist", description="Playlist commands", guild_only=True)

    @playlist.command(name="play", description="Play a playlist by name")
    @app_commands.describe(playlist="The name of the playlist.")
    async def playlist_play(self, interaction: discord.Interaction, playlist: str):
        ctx = await self.bot.get_context(interaction)
        # Aqui você pode chamar a lógica de playlist do seu Audio cog
        await interaction.response.send_message(f"Playlist '{playlist}' played!", ephemeral=True)

    # Adicione outros comandos de playlist conforme necessário

    # Utility para deletar mensagens embed do Audio cog original
    async def delete_audio_cog_embeds(self, ctx):
        async for msg in ctx.channel.history(limit=10):
            if msg.author == ctx.me and msg.embeds:
                embed = msg.embeds[0]
                if embed.title and any(
                    t in embed.title.lower() for t in [
                        "track paused", "track resumed", "volume", "track enqueued", "track added"
                    ]
                ):
                    try:
                        await msg.delete()
                    except Exception:
                        pass

    async def setup(bot):
        cog = EnhancedAudio(bot)
        await bot.add_cog(cog)
        # Registrar comandos slash
        bot.tree.add_command(cog.slash_play)
        bot.tree.add_command(cog.slash_pause)
        bot.tree.add_command(cog.slash_stop)
        bot.tree.add_command(cog.slash_skip)
        bot.tree.add_command(cog.slash_queue)
        bot.tree.add_command(cog.slash_repeat)
        bot.tree.add_command(cog.slash_shuffle)
        bot.tree.add_command(cog.slash_volume)
        bot.tree.add_command(cog.playlist)
