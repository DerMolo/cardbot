import discord
import zlib
from discord.ext import commands
import os 
import json
from dotenv import load_dotenv
import random
from enum import Enum

# --- Configuration & Setup ---
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
intents.guilds = True 

bot = commands.Bot(command_prefix="!", intents=intents)

rarityClass = {0.0027:"Legendary", 0.042:"Rare", 0.272:"Uncommon" , 1:"Common" }

def calcRarity(rarity):
    for percent in rarityClass:
        if rarity<=percent:
            return rarityClass[percent]

dbChannels = ["card-json", "user-json", "inventory-json","gallery-embed"]

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

class dbType(Enum): #dicates the target channel to search through
    CARD_JSON = 1
    USER_JSON = 2 
    INVENTORY_JSON = 3

dbTypeDict = {dbType.CARD_JSON:"card-json",
              dbType.USER_JSON:"user-json",
              dbType.INVENTORY_JSON:"inventory-json"}


#JSONs are needed to store information that's not necessarily displayed by embeds 
#It's a way to easily read messages into dicts. 
#I'm creating objects with some set of member variables so that each JSON can easily map to that 
#I currently don't think these classes are entirely necessary though. I'm mostly using them as frameworks for 
# the data each object type requires 

async def toJSON(ctx, data, type): #converts embed to JSON
    #data = a dict of json fields
    print(f"(convertJSON) passed type: {type}")
    targetDb = dbTypeDict[type]
    #updates json channel with corresponding json info
    targetChannel = discord.utils.get(ctx.guild.text_channels,name=targetDb)
    await targetChannel.send(json.dumps(data))
    await ctx.send(f"successfully updated {targetDb}")
    return
 


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

def createHash(dbObject):
    #return hashlib.sha1(json.dumps(dbObject).encode()).hexdigest()
    return format(zlib.crc32(json.dumps(dbObject).encode()) & 0xFFFFFFFF, '08x')

#CARD-STORING LOGIC==== 
@bot.command() 
@commands.is_owner()
async def createcard(ctx, title, img):
    prob = round(random.random(),5)
    rarity = calcRarity(prob)
    print(f"generated random: {prob}")
    print(f"generated rarity: {rarity}")
    #card = Card(title, ctx.author.name, img, rarity)
    dataList = {"Title":title,
                "Creator":ctx.author.name,
                "Owner":None,
                "Content":img,
                "Probability":prob,
                "Rarity":rarity
                }
    cardID = createHash(dataList)
    dataList["CardID"]=cardID

    cardEmbed = discord.Embed(title=title, description=f"\nCard ID: {cardID}\nCreated by: {ctx.author.name}\nRarity: {rarity}")
    cardEmbed.set_image(url=img)

    print(f"generated hash: {dataList["CardID"]}")
    await toJSON(ctx, dataList, dbType.CARD_JSON)
    await ctx.send(embed=cardEmbed)
    return
    #await storecard(ctx)

@bot.command()
async def searchcard(ctx, cardID):
    await search(ctx,dbType.CARD_JSON,cardID)
    return

# TODO:  
# add user/inventory updating logic that accounts for trading and daily claims 
# possible updates: 
# deletion, and creation 
# NOTE: 
# I might need to re-introduce pre-rendered galleries for inventories 

@bot.command()
async def givecard(ctx, cardID):
    search(ctx,dbType.CARD_JSON,cardID)
    return

@bot.command()
@commands.is_owner()
async def givecard(ctx, username, cardID):
    cardFound = await search(ctx,dbType.CARD_JSON,cardID)
    userFound = await search(ctx,dbType.USER_JSON,username)
    if  cardFound is None:  
        ctx.send("Card doesn't exist")
    elif userFound is None: 
        userFound = await createUser(ctx,username)
    
    return 

async def createUser(ctx, username):
    userJson = {
        "Username":username,
        "Balance":0.0
    }
    InventoryID = createHash(userJson)
    userJson["InventoryID"]=InventoryID
    userChannel = discord.utils.get(ctx.guild.text_channels, name="user-json")
    userEmbed = renderEmbed(ctx, dbType.USER_JSON, userJson)

async def search(ctx, type, ID): #returns a discord.message or None    
    targetDb = dbTypeDict[type]
    targetChannel = discord.utils.get(ctx.guild.text_channels,name=targetDb) 
    async for message in targetChannel.history(limit=None):
        if ID in message.content: 
            await renderEmbed(ctx,type,message.content)
            return message
    await ctx.send("Card not found")
    return None

async def renderEmbed(ctx,type,jsonData): #TODO: renderEmbed needs to account for inventories and users 
    if type.value == 1:
        strData = json.loads(jsonData)
        cardEmbed = discord.Embed(title=strData["Title"], description=f"\nCard ID: {strData["CardID"]}\nCreated by: {strData["Creator"]}\nRarity: {strData["Rarity"]}")
        cardEmbed.set_image(url=strData["Content"])
        await ctx.send(embed=cardEmbed)
        return cardEmbed
    if type.value == 2:  #NOTE: only gallery embeds are accessed for json information, everything else is stored as a json
        strData = json.loads(jsonData)
        cardEmbed = discord.Embed(title=strData["Username"], description=f"\nInventory ID: {strData["InventoryID"]}\nBalance: {strData["Balance"]}")
        await ctx.send(embed=cardEmbed)
        return cardEmbed
    
async def renderGallery(ctx,jsonData): #redundant bruhaps (consolidated via renderEmbed)
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

async def storecard(ctx, cardID):
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