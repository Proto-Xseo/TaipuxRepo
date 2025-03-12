from discord.ext import commands
import random

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gacha")
    async def gacha_command(self, ctx):
        await ctx.send("Gacha command triggered!")

async def setup(bot):
    await bot.add_cog(Gacha(bot))
