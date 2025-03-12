from discord.ext import commands

class PVE(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This is a placeholder for your PvE battle system.
    @commands.command(name="pve")
    async def trade(self, ctx):
     await ctx.send("Pve Acctivated.")

async def setup(bot):
    await bot.add_cog(PVE(bot))


