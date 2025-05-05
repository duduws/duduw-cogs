```markdown
# Enhanced_Audio

**Enhanced_Audio** is a cog for Redbot that enhances the original Audio cog. It replaces and improves some of the default Audio commands, providing a better user experience when controlling music playback.

## Features

- **Interactive Interface:** Uses custom buttons (play/pause, stop, skip, repeat, shuffle, etc.) to make music control easier.
- **Improved Embeds:** Displays the current song, queue, and status with more informative and visually appealing embeds.
- **Command Overrides:** Replaces default Audio cog commands with enhanced versions:
  - `play [query]`: Searches and plays music with an improved interactive interface.
  - `now`: Shows the currently playing song with interactive controls.
  - `queue`: Displays the music queue in pages.
  - `skip`: Skips the current track and updates the interactive embed.
- **Inactivity Check:** Periodically updates the interactive embed and removes old messages if inactive.

## Installation

1. **Requirements:**  
   - Make sure the original `Audio` cog for Redbot is installed and properly configured. Enhanced_Audio depends on it to function correctly.

2. **Installing Enhanced_Audio:**  
   - Download or clone this repository into your Redbot cogs folder.
   - Ensure all required dependencies (such as `discord.py`, `lavalink`, etc.) are installed in the environment where Redbot is running.
   - Load the cog using the following command in your Discord server:  
     ```
     [p]load Enhanced_Audio
     ```

## Usage

- **`play [query]`**  
  Searches and plays the specified song, displaying an improved interactive interface with controls.

- **`now`**  
  Shows the currently playing track with buttons for pausing, skipping, repeating, etc.

- **`queue`**  
  Displays the playback queue in a paginated format, allowing navigation through the song list.

- **`skip`**  
  Skips the current song and updates the embed with the next track's information.

> ⚠️ These commands override the original ones from the Audio cog. When using commands like `[p]play`, Redbot will use Enhanced_Audio's version instead of the default.

## Configuration

This cog uses Redbot’s configuration system to store per-guild settings such as repeat state and shuffle mode. It also runs a background task to check for inactivity and clean up old messages.

## Contributing

Contributions are welcome! If you'd like to suggest improvements or report issues, please open an issue or submit a pull request on this repository.
```
