from discord.ext import commands

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        await ctx.send("Leaderboard placeholder.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
