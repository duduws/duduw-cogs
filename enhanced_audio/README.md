# enhanced_audio

**enhanced_audio** is a cog for Redbot that enhances the original Audio cog. It replaces and improves the default Audio commands, providing a modern and interactive music experience with beautiful embeds and full slash command support.

## Features

- **Modern Slash Commands:** Use `/play`, `/pause`, `/queue`, `/skip`, `/stop`, `/volume`, `/repeat`, `/shuffle`, `/playlist` and more directly from Discord's UI.
- **Custom Now Playing Embed:**
  - Shows the guild name as author (with a custom link and icon).
  - Music name is bold, clickable, and uses the song's image as thumbnail.
  - Queue shows the number of tracks.
  - Volume and requester are clearly displayed, with the requester always mentioned.
  - Status fields for repeat, shuffle, and auto-play.
- **Ephemeral Responses:** All control actions (pause, skip, volume, etc.) reply only to the user who requested, keeping the chat clean.
- **Command Overrides:** Replaces default Audio cog commands with enhanced versions, including slash commands.
- **Inactivity Check:** Periodically updates the interactive embed and removes old messages if inactive. The bot will always disconnect from the voice channel after inactivity.
- **Auto-cleanup:** Any embed messages from the original Audio cog (like "Track Paused", "Track Resumed", "Volume") are automatically deleted for a clean experience.

## Installation

1. **Requirements:**  
   - Make sure the original `Audio` cog for Redbot is installed and properly configured. enhanced_audio depends on it to function correctly.
   - You need a working Lavalink server. See [Lavalink Setup Guide](https://github.com/freyacodes/Lavalink#server-setup).

2. **Installing enhanced_audio:**  
   - Download or clone this repository into your Redbot cogs folder.
   - Ensure all required dependencies (such as `discord.py`, `lavalink`, etc.) are installed in the environment where Redbot is running.
   - Load the cog using the following command in your Discord server:  
     ```
     [p]load enhanced_audio
     ```
   - **Tip:** Use `/play` to start music instantly! All main controls are available as slash commands for a modern Discord experience.

## Usage

- **`/play [query]`**  
  Searches and plays the specified song, displaying a beautiful interactive embed with controls.

- **`/pause`, `/skip`, `/stop`, `/queue`, `/repeat`, `/shuffle`, `/volume`**  
  All main controls are available as slash commands and respond only to you (ephemeral).

- **Queue and Playlist**  
  The queue shows the number of tracks and can be managed with buttons or slash commands.

> ⚠️ These commands override the original ones from the Audio cog. When using commands like `/play`, Redbot will use enhanced_audio's version instead of the default.

## Configuration

This cog uses Redbot's configuration system to store per-guild settings such as repeat state and shuffle mode. It also runs a background task to check for inactivity and clean up old messages and disconnect from voice channels.

## Contributing

Contributions are welcome! If you'd like to suggest improvements or report issues, please open an issue or submit a pull request on this repository.
