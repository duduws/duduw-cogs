from redbot.core.bot import Red

from .enhanced_audio import EnhancedAudio


async def setup(bot: Red) -> None:
    await bot.add_cog(EnhancedAudio(bot))
