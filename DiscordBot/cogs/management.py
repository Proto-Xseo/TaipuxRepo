import discord
from discord.ext import commands
from utils.db import get_user, update_user

EMOJI = {
    "currency": "<:gold:1345000286128832606>",
    "gacha_tickets": "<:gacha:1345000464399470645>",
    "premium_token": "<:echo:1345000283276705875>",
    "shards": "<:shards1:1345000988720758814>",
    "boosts": "<:shards:1345000347936227422>"
}

class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="wishlist", invoke_without_command=True)
    async def wishlist(self, ctx):
        user_data = get_user(ctx.author.id)
        wishlist = user_data.get("wishlist", [])
        if not wishlist:
            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s Wishlist",
                description="Your wishlist is empty! Add characters with `!wishlist add <character_name>`",
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
        else:
            # Create paginated wishlist view
            view = WishlistView(wishlist, ctx.author)
            embed = view.get_embed()
            await ctx.send(embed=embed, view=view)

    @wishlist.command(name="add")
    async def wishlist_add(self, ctx, *, waifu: str):
        user_data = get_user(ctx.author.id)
        wishlist = user_data.get("wishlist", [])
        if waifu in wishlist:
            await ctx.send("That waifu is already in your wishlist!")
        else:
            wishlist.append(waifu)
            update_user(ctx.author.id, "wishlist", wishlist)
            
            # Update character wishlist count in ALL_CHARACTERS if available
            try:
                from cogs.lookup import ALL_CHARACTERS
                waifu_key = waifu.strip().lower()
                if waifu_key in ALL_CHARACTERS:
                    char_data = ALL_CHARACTERS[waifu_key]
                    wishlist_count = char_data.get('wishlists', 0)
                    if isinstance(wishlist_count, str) and wishlist_count == 'N/A':
                        wishlist_count = 0
                    char_data['wishlists'] = wishlist_count + 1
            except (ImportError, AttributeError):
                pass  # Silently fail if lookup module not available
                
            embed = discord.Embed(
                title="Wishlist Updated",
                description=f"Added **{waifu}** to your wishlist!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

    @wishlist.command(name="remove")
    async def wishlist_remove(self, ctx, *, waifu: str):
        user_data = get_user(ctx.author.id)
        wishlist = user_data.get("wishlist", [])
        if waifu not in wishlist:
            await ctx.send("That waifu is not in your wishlist!")
        else:
            wishlist.remove(waifu)
            update_user(ctx.author.id, "wishlist", wishlist)
            
            # Update character wishlist count in ALL_CHARACTERS if available
            try:
                from cogs.lookup import ALL_CHARACTERS
                waifu_key = waifu.strip().lower()
                if waifu_key in ALL_CHARACTERS:
                    char_data = ALL_CHARACTERS[waifu_key]
                    wishlist_count = char_data.get('wishlists', 0)
                    if isinstance(wishlist_count, str) and wishlist_count == 'N/A':
                        wishlist_count = 1
                    char_data['wishlists'] = max(0, wishlist_count - 1)
            except (ImportError, AttributeError):
                pass  # Silently fail if lookup module not available
                
            embed = discord.Embed(
                title="Wishlist Updated",
                description=f"Removed **{waifu}** from your wishlist!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
class WishlistButton(discord.ui.Button):
    def __init__(self, label, parent_view, action: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.action = action
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            await interaction.response.send_message("This isn't your wishlist!", ephemeral=True)
            return
        
        if self.action == "first":
            self.parent_view.current_page = 0
        elif self.action == "prev" and self.parent_view.current_page > 0:
            self.parent_view.current_page -= 1
        elif self.action == "next" and self.parent_view.current_page < len(self.parent_view.pages) - 1:
            self.parent_view.current_page += 1
        elif self.action == "last":
            self.parent_view.current_page = len(self.parent_view.pages) - 1
        
        await self.parent_view.update_message(interaction)

class WishlistView(discord.ui.View):
    def __init__(self, wishlist, author: discord.Member):
        super().__init__(timeout=120)
        self.author = author
        self.wishlist = wishlist
        self.items_per_page = 10
        self.pages = [wishlist[i:i+self.items_per_page] for i in range(0, len(wishlist), self.items_per_page)]
        self.current_page = 0
        
        # Add navigation buttons if we have multiple pages
        if len(self.pages) > 1:
            self.add_item(WishlistButton("⏮️", self, "first"))
            self.add_item(WishlistButton("◀️", self, "prev"))
            self.add_item(WishlistButton("▶️", self, "next"))
            self.add_item(WishlistButton("⏭️", self, "last"))
    
    def get_embed(self):
        if not self.pages:
            return discord.Embed(
                title=f"{self.author.display_name}'s Wishlist",
                description="Your wishlist is empty!",
                color=discord.Color.purple()
            )
        
        # Format the wishlist items with numbers
        formatted_items = []
        start_idx = self.current_page * self.items_per_page
        for i, item in enumerate(self.pages[self.current_page], 1):
            formatted_items.append(f"{start_idx + i}. **{item}**")
        
        embed = discord.Embed(
            title=f"{self.author.display_name}'s Wishlist",
            description="\n".join(formatted_items),
            color=discord.Color.purple()
        )
        
        # Add pagination info
        total_items = len(self.wishlist)
        embed.set_footer(text=f"Page {self.current_page+1}/{len(self.pages)} • {total_items} character{'s' if total_items != 1 else ''}")
        
        return embed
    
    async def update_message(self, interaction: discord.Interaction):
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    @commands.command(name="inventory")
    async def inventory(self, ctx):
        user_data = get_user(ctx.author.id)
        currency = user_data.get("currency", 0)
        tickets = user_data.get("gacha_tickets", 0)
        boosts = user_data.get("boosts", 0)
        shards = user_data.get("shards", 0)
        premium = user_data.get("premium_token", 0)
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Inventory",
            description=(
                f"{EMOJI['currency']} **Currency:** {currency}\n"
                f"{EMOJI['gacha_tickets']} **Gacha Tickets:** {tickets}\n"
                f"{EMOJI['premium_token']} **Premium Tokens:** {premium}\n"
                f"{EMOJI['shards']} **Shards:** {shards}\n"
                f"{EMOJI['boosts']} **Boosts:** {boosts}"
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="view")
    async def view_card(self, ctx, *args):
        if not args:
            await ctx.send("Usage: !view <global_id> or !view -user <user_id> <card_order>")
            return
        card = None
        if args[0] == "-user":
            if len(args) < 3:
                await ctx.send("Usage: !view -user <user_id> <card_order>")
                return
            try:
                target_id = int(args[1])
                order = int(args[2])
                user_data = get_user(target_id)
                for c in user_data.get("cards", []):
                    if c.get("order") == order:
                        card = c
                        break
            except Exception as e:
                await ctx.send("Error fetching user or card.")
                return
        else:
            global_id = args[0]
            user_data = get_user(ctx.author.id)
            for c in user_data.get("cards", []):
                if c.get("global_id") == global_id:
                    card = c
                    break
        if not card:
            await ctx.send("Card not found.")
            return
        embed = discord.Embed(
            title=f"{card.get('name')} (Global ID: {card.get('global_id')})",
            description=(
                f"**Character ID:** {card.get('character_id')}\n"
                f"**Series:** {card.get('series')}\n"
                f"**Affection:** {card.get('affection', 0)}\n"
                f"**Claimed by:** {card.get('claimed_by')}"
            ),
            color=0xFFD700
        )
        if card.get("claimed_artwork"):
            embed.set_image(url=card["claimed_artwork"])
            embed.set_thumbnail(url=card["claimed_artwork"])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Management(bot))
