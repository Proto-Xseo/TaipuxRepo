import discord
from discord.ext import commands
from utils.db import get_user
import io

# Custom UI view for image navigation
class PreviewView(discord.ui.View):
    def __init__(self, images: list):
        super().__init__(timeout=120)
        self.images = images
        self.current_index = 0
        # Create navigation buttons
        self.add_item(PreviewButton("first", "<:first:1347598533653430443>"))
        self.add_item(PreviewButton("prev", "<:prev:1347598835295453346>"))
        self.add_item(PreviewButton("next", "<:next:1347642109359816895>"))
        self.add_item(PreviewButton("last", "<:last:1347596578751250565>"))
    
    def update_buttons(self):
        total = len(self.images)
        for child in self.children:
            if isinstance(child, PreviewButton):
                if child.action in ["first", "prev"]:
                    child.disabled = self.current_index == 0
                elif child.action in ["next", "last"]:
                    child.disabled = self.current_index >= total - 1
    
    def get_current_image(self) -> str:
        return self.images[self.current_index] if self.images else "https://via.placeholder.com/800x600"
    
    def generate_embed(self, card: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"Preview: {card.get('name', 'Unknown')}",
            description=(
                f"**Series:** {card.get('series', 'Unknown')}\n"
                f"**Rarity:** {card.get('rarity', 'Unknown')}\n"
                f"**Affection:** {card.get('affection', 0)}"
            ),
            color=discord.Color.purple()
        )
        embed.set_image(url=self.get_current_image())
        embed.set_footer(text=f"Image {self.current_index + 1} of {len(self.images)}")
        return embed

class PreviewButton(discord.ui.Button):
    def __init__(self, action: str, emoji: str):
        super().__init__(label="", emoji=emoji, style=discord.ButtonStyle.primary, custom_id=action)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: PreviewView = self.view
        if self.action == "first":
            view.current_index = 0
        elif self.action == "prev" and view.current_index > 0:
            view.current_index -= 1
        elif self.action == "next" and view.current_index < len(view.images) - 1:
            view.current_index += 1
        elif self.action == "last":
            view.current_index = len(view.images) - 1
        view.update_buttons()
        # Edit the original message with the updated embed
        new_embed = view.generate_embed(view.card)
        await interaction.response.edit_message(embed=new_embed)

class Preview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="view", aliases=["v"])
    async def view(self, ctx, card_id: str):
        """
        Preview a card from your collection.
        Usage: !view <card_global_id>
        This command will display an embed with the card's details and allow you to navigate all associated images.
        """
        user_data = get_user(ctx.author.id)
        if not user_data:
            return await ctx.send("No profile data found, please claim some cards first!")
        
        # Find the card by its global_id in the user's collection
        cards = user_data.get("cards", [])
        card = next((c for c in cards if c.get("global_id") == card_id), None)
        if not card:
            return await ctx.send("Card not found in your collection!")
        
        # Gather all images from the card:
        # Try primary_image first, then fallback to claimed_artwork, then extra_images.
        images = []
        primary = card.get("primary_image", {}).get("url")
        if primary:
            images.append(primary)
        elif card.get("claimed_artwork"):
            images.append(card.get("claimed_artwork"))
        extras = card.get("extra_images", [])
        for extra in extras:
            url = extra.get("url")
            if url:
                images.append(url)
        if not images:
            images.append("https://via.placeholder.com/800x600")
        
        # Create a PreviewView with the list of images and assign the card for use in embed generation.
        view_instance = PreviewView(images)
        view_instance.card = card  # Store card details in the view for later use
        
        # Build the initial embed
        embed = view_instance.generate_embed(card)
        await ctx.send(embed=embed, view=view_instance)

async def setup(bot):
    await bot.add_cog(Preview(bot))
