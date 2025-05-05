from redbot.core.bot import Red

from .enchanced_audio import EnchancedAudio


async def setup(bot: Red) -> None:
    await bot.add_cog(EnchancedAudio(bot))
