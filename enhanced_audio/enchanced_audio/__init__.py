from .enhanced_audio import EnhancedAudio

async def setup(bot):
    await bot.add_cog(EnhancedAudio(bot)) 