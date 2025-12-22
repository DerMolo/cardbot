import discord
import math
from discord import app_commands
from discord.ext import commands
import os 
import json
from dotenv import load_dotenv
import random
# --- Configuration & Setup ---
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
intents.guilds = True 

bot = commands.Bot(command_prefix="!", intents=intents)


dbChannels = ["card-json", "card-embed","user-json","user-embed", "inventory-json","inventory-embed", "array-json"]

#User data model: 
#inventory hash 
#username
#user hash 
#card count

#class Card:
#    def __init__(self, title, creator, cardImg, rarity):
#        self.title = title
#        self.creator = creator
#        self.cardImg = cardImg
#        self.rarity = rarity

class dbType(Enum):
    CARD_JSON = 1
    ARRAY_JSON = 2 #stores an array of card hashes per inventory 
    USER_JSON = 3 
    INVENTORY_JSON = 4

#JSONs are needed to store information that's not necessarily displayed by embeds 
#It's a way to easily read messages into dicts. 
#I'm creating objects with some set of members variables so that each JSON can easily map to that 
#I currently don't think these classes are entirely necessary though. I'm mostly using them as frameworks for 
# the data each object type requires 

async def convertToJSON(ctx, embed, type):
    if dbType(type) == 1: #CARD_JSON
        for key in embed.to_dict(): 
            temp = embed.to_dict()[key]
            print(f"{temp}")


def checkRole(roleA, roleList):
    if roleA.name == "@everyone":
        return False 
    for role in roleList: 
        if role == roleA: 
            return True
    return False

async def initDatabase(guild): 
    print(f"initDatabase accessed for {guild.name}")
    modCategory = discord.utils.get(guild.categories, name="bot-data")
    
    # Accessing channels
    foundChannels = {} 
    for name in dbChannels: 
        foundChannels[name] = discord.utils.get(guild.text_channels,name=name)

    missingChannels = []
    for name in foundChannels:
        temp = foundChannels[name] 
        if temp is None: 
            missingChannels.append(name)
    
    if not missingChannels: 
        print(f"Database channels exist in {guild.name}")
    else: 
        print(f"Missing channels in {guild.name}. Initializing...")
        if modCategory is None:
            overwrites = {} 
            for role in guild.roles:
                # guild.me refers to the bot's member object in this specific guild
                if checkRole(role, guild.me.roles):
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                elif checkRole(role, guild.owner.roles):
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
                else:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=False)
            
            modCategory = await guild.create_category(name="bot-data", overwrites=overwrites)
        
        for channelName in missingChannels: 
            await guild.create_text_channel(name=channelName, category=modCategory)             

@bot.event
async def on_ready():
    print(f"Ready for anything. Logged in as: {bot.user.name}")
    for guild in bot.guilds: 
        await initDatabase(guild)

@bot.command()
async def daily(ctx, coin):
    prob = {"Legendary": 0.0027, "Rare": 0.042, "Uncommon": 0.272, "Common": 0.682} 
    # Placeholder for daily logic
    await ctx.send(f"Daily rewards for {coin} coins requested.")

@bot.command()
@commands.is_owner()
async def removedb(ctx): 
    print("removedb accessed")
    guild = ctx.guild
    modCategory = discord.utils.get(guild.categories, name="bot-data")
    
    if modCategory: 
        await modCategory.delete()
    
    for channelName in dbChannels:
        temp = discord.utils.get(guild.text_channels, name=channelName)
        if temp: 
            await temp.delete()
    await ctx.send("Database channels and category removed.")

@bot.command()
@commands.is_owner()
async def cleardb(ctx): 
    guild = ctx.guild
    modCategory = discord.utils.get(guild.categories, name="bot-data")
    if modCategory: await modCategory.delete()
    for name in dbChannels:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch: await ch.delete()

    await initDatabase(guild)
    await ctx.send("Database cleared and re-initialized.")

#CARD-STORING LOGIC==== 
@bot.command() 
async def createcard(ctx, title, img):
    rarity = round(random.random(),5)
    print(f"generated random: {rarity}")
    cardEmbed = discord.Embed(title=title, description=f"Created by: {ctx.author.name}\nRarity: {round(rarity*100,5)}%")
    cardEmbed.set_image(url=img)
    card = Card(title, ctx.author.name, img, rarity)
    await convertToJSON(ctx, cardEmbed, CARD)
    await ctx.send(embed=cardEmbed)
    await storecard(ctx, card)


async def renderEmbed(ctx): 
    return 

async def renderGallery(): 
    return 

async def renderInventory():
     #class DropdownView(discord.ui.View):
      #  @discord.ui.select(
      #      placeholder="Choose a card type...",
      #      options=[
      #          discord.SelectOption(label="Monster", value="1", description="Creature cards"),
      #          discord.SelectOption(label="Spell", value="2", description="Magic cards")
      #      ]
      #  )
    return 

async def storecard(ctx, card):
    return

#+++++==== 

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

@bot.command()
async def test(ctx, arg1, arg2):
    if arg1 == "fuck" and arg2 == arg1:
        await ctx.send("you've copied my flow")
    else: 
        await ctx.send("FUCK YEAH!")

bot.run(token)