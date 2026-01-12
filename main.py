import discord
#from discord.ui import Select, View, Button
from discord.ext import commands
import os 
import json
from dotenv import load_dotenv
import random
from enum import Enum
import math
from functools import partial

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

dbChannels = ["card-json", "user-json", "inventory-json","card-inbox"]


#NOTE: dbType is most likely useless. It's currently used to map
#channel-specific functions their intended channel 
# Refactoring would simply involve passing the channel itself to 
# relevant function (instead of a dbType type) 
#
# using dbType is forcing a redundant invocation of discord.utils.get
# which may trigger rate limiting 
#
#I'll refactor whenever that issue occurs :)
#

#TODO: Update sendEmbedFromJson such that it accounts for inventories. 
# Figure out how inventories are going to be displayed. 
# Continue implementing database logic that updates, and creates the expected entries. Currently, there's no 
# Update logic for Users, Inventories (and by proxy, galleries)
# givecard still doesn't account for pre-existing users 




    #NOTE: far-off idea for handling json entries that exceed discord's message limit 
    # reading message length before appending data. 
    # Each entry contains a "ParentID" that essentially functions like a linked list 
    # Inventory JSON *case where the number of stored CardIDs exceed the limit 
    # InvID = 123, ParentID= Null, ChildID = 145, ...... 
    # InvID = 145, ParentID = 123, ChildID = Null, ..... etc 
    #
    # IF outgoingJson.length() + fetch_message(targetID).length() >= discordLimit then: 
    #  create a new message 
    # extract the ID 
    # update outgoingJson's parentID to targetID 
    # update the message(targetID)'s childID to outgoingJson's newID 
    # add new entry 
    # (copy over the inventory header metadata, if outgoingJson is an inventory type)
    # *This issue will only ever occur with inventory

    #    invDict = {
    #    "Cards":1,
    #    "Username":username,
    #   "UserID":userID,
    #    "InventoryID":createID(ctx,dbType.INVENTORY_JSON),
    #   "CardIDs":[card]
    #}


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

async def storeJSON(ctx, dbDict, ID, type): #converts dict to JSON and sends to appropriate json text-channel
    #data = a dict of json fields
    print(f"(convertJSON) passed type: {type}")
    targetDb = dbTypeDict[type]
    #updates json channel with corresponding json info
    targetChannel = discord.utils.get(ctx.guild.text_channels,name=targetDb)
    targetMessage = await targetChannel.fetch_message(ID)

    jsonData = json.dumps(dbDict)
    await targetMessage.edit(content=jsonData)
    print(f"generated json: {jsonData}")
    
    #await targetChannel.send(json.dumps(data))
    await ctx.send(f"successfully updated {targetDb}")
    return jsonData
 
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
    if modCategory: 
        await modCategory.delete()
    for name in dbChannels:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch: 
            await ch.delete()

    await initDatabase(guild)
    await ctx.send("Database cleared and re-initialized.")

#CARD-STORING LOGIC==== 
@bot.command() 
@commands.is_owner()
async def createcard(ctx, title, img):
    prob = round(random.random(),5)
    rarity = calcRarity(prob)
    print(f"generated random: {prob}")
    print(f"generated rarity: {rarity}")
    #card = Card(title, ctx.author.name, img, rarity)
    cardDict = {"Title":title,
                "Availability":True,
                "Creator":ctx.author.name,
                "Owner":None,
                "Content":img, #URL to image
                "Probability":prob,
                "Rarity":rarity,
                "CardID":await createID(ctx,dbType.CARD_JSON)
                }

    print(f"Card-json message id: {cardDict["CardID"]}")
    cardJson = await storeJSON(ctx, cardDict, cardDict["CardID"], dbType.CARD_JSON)
    await sendEmbedFromJson(ctx,dbType.CARD_JSON,cardJson)
    return cardDict["CardID"]

async def updateInv(ctx,invID,dictChanges):
    invFound = await silentSearch(ctx, type, invID)
    if invFound is None: 
        print("updateEntry: Target item not found")
        return 
    entryDict = json.loads(invFound.content)
    for field, change in dictChanges.items():
        if field == "CardCount":
            entryDict[field]+=change
        elif field == "CardIDs":
            #format for changing CardIDs, 
            # <field> : [-1/1, <CardID>]
            # -1 = remove card, 1 = add card
            if change[0] == -1: 
                entryDict[field].remove(change[1]) 
            else: 
                entryDict[field].append(change[1])
        await ctx.send(f"Successfully updated {dbTypeDict[type]} channel. Field: {field}, Change: {change}")
    await invFound.edit(content=json.dumps(entryDict))    

@bot.command()
@commands.is_owner() 
async def freecard(ctx,cardID):
    cardFound = await silentSearch(ctx,dbType.CARD_JSON,cardID)
    cardFound = json.loads(cardFound.content)
    ownerFound = await silentSearch(ctx,dbType.USER_JSON,cardFound["Owner"])
    ownerFound = json.loads(ownerFound.content)
    inventoryFound = await silentSearch(ctx,dbType.INVENTORY_JSON,ownerFound["InventoryID"])
    inventoryFound = json.loads(inventoryFound.content)
    dChanges = {
        ""

    }

    dChanges = {
        "Availability":True,
        "Owner":None
    }
    await updateEntry(ctx,cardID,dbType.CARD_JSON,dChanges)
    #await storecard(ctx)

#Idea for creating IDs for each message 
#Pre-sending a message with a unique ID
#Retrieving that ID and returning it
#The caller then uses that message as a unique entry for data storage

async def createID(ctx, type):
    channelName = dbTypeDict.get(type)
    
    if not channelName:
        print(f"Error: No channel name mapped for dbType: {type}")
        return None
    channel = discord.utils.get(ctx.guild.text_channels, name=channelName)
    
    if channel is None:
        # Debugging: List available channels
        available = [c.name for c in ctx.guild.text_channels]
        print(f"Error: Could not find channel '{channelName}'.")
        print(f"Available channels: {available}")
        return None

    msg = await channel.send(content="\u200b")
    return msg.id

#SEARCH FUNCTIONS  
@bot.command()
async def searchcard(ctx, cardID):
    await search(ctx,dbType.CARD_JSON,cardID)
    return

async def search(ctx, type, ID): #returns a discord.message or None    
    targetDb = dbTypeDict[type]
    targetChannel = discord.utils.get(ctx.guild.text_channels,name=targetDb)
    if not type == dbType.USER_JSON:
        try:  
            message = await targetChannel.fetch_message(ID)
        except discord.NotFound: 
            await ctx.send(f"(search) Entry in {targetDb} not found")
            return None
        await ctx.send(f"(search) Entry in {targetDb} found")
        await sendEmbedFromJson(ctx,type,message.content)
        return message
    else: #CURRENT WORKAROUND FOR USING USERNAMES INSTEAD OF USERID 
        #TODO: FIND A WAY TO MAP USERNAMES TO USERIDS 
        async for message in targetChannel.history(limit=None): #LINEAR SEARCH APPROACH 
            if ID in message.content:
                ctx.send(f"(linear search) Entry in {targetDb} found") 
                await sendEmbedFromJson(ctx,type,message.content)
                return message
        await ctx.send(f"(linear search) Entry in {targetDb} not found")
        return None

async def silentSearch(ctx, type, ID): 
    targetDb = dbTypeDict[type]
    targetChannel = discord.utils.get(ctx.guild.text_channels,name=targetDb)
    if not type == dbType.USER_JSON:
        try:  
            message = await targetChannel.fetch_message(ID)
        except discord.NotFound: 
            print(f"(search) Entry in {targetDb} not found")
            return None
        print(f"(search) Entry in {targetDb} found")
        #await sendEmbedFromJson(ctx,type,message.content)
        return message
    else: #CURRENT WORKAROUND FOR USING USERNAMES INSTEAD OF USERID 
        #TODO: FIND A WAY TO MAP USERNAMES TO USERIDS 
        async for message in targetChannel.history(limit=None): #LINEAR SEARCH APPROACH 
            if ID in message.content:
                print(f"(linear search) Entry in {targetDb} found") 
                #await sendEmbedFromJson(ctx,type,message.content)
                return message
        print(f"(linear search) Entry in {targetDb} not found")
        return None    


# TODO:  
# add user/inventory updating logic that accounts for trading and daily claims 
# possible updates: 
# deletion, and creation 
# NOTE: 
# I might need to re-introduce pre-rendered galleries for inventories 

@bot.command() 
async def inventory(ctx, username):
    userFound = await silentSearch(ctx,dbType.USER_JSON,username)
    userDict = json.loads(userFound.content)
    await search(ctx,dbType.INVENTORY_JSON,userDict["InventoryID"])


@bot.command()
@commands.is_owner() 
async def givecard(ctx, username, cardID):
    cardFound = await silentSearch(ctx,dbType.CARD_JSON,cardID)
    userFound = await silentSearch(ctx,dbType.USER_JSON,username)
    if cardFound is None:
        await ctx.send("Card doesn't exist")  
        return
    if userFound is None:
        await ctx.send("Initializing user entry")
        await createUser(ctx,username,cardFound.content)
        return
    else: 
        userFound = json.loads(userFound.content)
        cardFound = json.loads(cardFound.content)
        inventoryFound = await silentSearch(ctx,dbType.INVENTORY_JSON,userFound["InventoryID"])
        invJson = json.loads(inventoryFound.content)
        if not cardFound["Availability"]:
            invJson["CardIDs"].append(cardFound["CardID"])
            invJson["CardCount"] += 1 
        else: 
            await ctx.send(f"Card is already owned by {cardFound["Owner"]}")
        await inventoryFound.edit(content=json.dumps(invJson))
    dChanges = {
        "Owner" : username,
        "Availability" : False
    }
    await updateEntry(ctx,cardID,dbType.CARD_JSON,dChanges)

#ENTRY CREATION 
async def createUser(ctx, username: str, cardJson: str):
    card = json.loads(cardJson)
    userDict = {
        "Username":username,
        "Balance":0.0,
        "UserID":await createID(ctx,dbType.USER_JSON)
    }
    userDict["InventoryID"] = await createInventory(ctx, username,userDict["UserID"], card)
    await storeJSON(ctx, userDict, userDict["UserID"],dbType.USER_JSON) #update user-json
    await sendEmbedFromJson(ctx, dbType.USER_JSON, str(userDict))
    return userDict["UserID"] 
    

async def createInventory(ctx, username, userID, cardDict):
    # Username
    # Gallery hash 
    # Inventory hash 
    # Card Count
    invDict = {
        "CardCount":1,
        "Username":username,
        "UserID":userID,
        "InventoryID":await createID(ctx,dbType.INVENTORY_JSON),
        "CardIDs":[cardDict["CardID"]], 
    }
    if not cardDict["Availability"]: 
        invDict["CardCount"] = 0
        invDict["CardIDs"] = []
    else: 
        dChanges = {
        "Owner" : username,
        "Availability" : False
        }
        await updateEntry(ctx,cardDict["CardID"],dbType.CARD_JSON,dChanges)

    await ctx.send(f"Inventory-json message id for {invDict["Username"]}: {invDict["InventoryID"]}")
    print(f"inventory-json message id: {invDict["InventoryID"]}")
    invJson = await storeJSON(ctx, invDict, invDict["InventoryID"],dbType.INVENTORY_JSON) #update user-json
    #typically use sendEmbedFromJson to display the inventory. 
    await sendEmbedFromJson(ctx, dbType.INVENTORY_JSON, invJson) 
    return invDict["InventoryID"]

#UPDATE FUNCTIONS 
#async def updateUserBalance(ctx,userID,balance):
#    userJson = await search(ctx, dbType.USER_JSON, userID)
#    if userJson is None:
#        print("updateUserBalance: No user found") 
#        return 
#    userDict = json.loads(userJson.content)
#    userDict["Balance"] = balance
#    await userJson.edit(content=json.dumps(userDict))

#async def updateCard(ctx,cardID,username):
#    cardJson = await search(ctx, dbType.CARD_JSON, cardID)
#    if cardJson is None:
#        print("updateCard: No card found") 
#        return 
#    userDict = json.loads(cardJson.content)
#    userDict["Owner"] = username
 #   await cardJson.edit(content=json.dumps(userDict))

#Generalizing entry changes 
#NOTE: Only applicable to USERS and CARDS
async def updateEntry(ctx,ID,type,dictChanges):
    jsonEntry = await silentSearch(ctx, type, ID)
    if jsonEntry is None: 
        print("updateEntry: Target item not found")
        return 
    entryDict = json.loads(jsonEntry.content)
    for field, change in dictChanges.items():
        if type == dbType.INVENTORY_JSON:
            if field == "CardCount":
                entryDict[field]+=change
            elif field == "CardIDs":
                #format for changing CardIDs, 
                # <field> : [-1/1, <CardID>]
                # -1 = remove card, 1 = add card
                if change[0] == -1: 
                    entryDict[field].remove(change[1]) 
                else: 
                    entryDict[field].append(change[1])             
        else: 
            entryDict[field]=change
        await ctx.send(f"Successfully updated {dbTypeDict[type]} channel. Field: {field}, Change: {change}")
    await jsonEntry.edit(content=json.dumps(entryDict))
        
#TODO: Update givecard to prevent duplicate cards from being given 

async def updateInventory(ctx,invID,cardID):
    
    return 

#NOTE: (something to handle later on)
# persistent view issues
# interaction failure issues          

class inventoryView(discord.ui.View):
    def __init__(self,embedList, optionList):
        super().__init__(timeout=180)
        self.embedList = embedList #embeds displayed when selected 
        self.optionList = optionList #consolidating every 25 card options into a page within pageList 
        #self.cardDicts = cardDicts 

        self.pageIndex = 0
        self.maxPageSize = math.ceil(len(embedList)/25)
        self.assemblePage(self.pageIndex)

    def assemblePage(self,pIndex):
        self.clear_items() 
        print(f"assemblePage: maxPageSize: {self.maxPageSize} ,pIndex: {pIndex}")
        if len(self.optionList) > 1: #adding next page button for pagelists greater than one 
            nextButton = discord.ui.Button(label="Next Page", custom_id=f"{pIndex}")
            nextButton.callback = partial(self.nextPageCallback, forward = True)
            if pIndex > 0: 
                prevButton = discord.ui.Button(label="Prev Page", custom_id=f"{pIndex}")
                prevButton.callback = partial(self.nextPageCallback, forward = False)
                self.add_item(prevButton)
            self.add_item(nextButton)

        #currentMedia = self.pageList[pIndex]
        #self.add_item(discord.ui.MediaGallery(*currentMedia))

        #pageMaxRange = len(self.optionList[pIndex]) #set of cards within the given page 
        #necessary for properly button.IDs to their corresponding embed 

        self.selectMenu = discord.ui.Select(
            placeholder="Choose a card",
            options = self.optionList[pIndex]
        )
        self.selectMenu.callback = self.selectCard 
        self.add_item(self.selectMenu)
        #for index in range(pageMaxRange): # pageIndex * 10 + offset 
        #    cardIndex = pIndex*10+index
        #    dict = self.cardDicts[cardIndex]
            #galleryButton = discord.ui.Button(label=f"Inspect {dict["Title"]}", custom_id=f"{cardIndex}")
            #galleryButton.callback=self.gallerySelectionCallback
            

            #self.add_item(galleryButton)
    
    async def returnCallback(self, interaction: discord.Interaction):
        #self.clear_items()
        self.assemblePage(self.pageIndex)
        await interaction.response.edit_message(view=self)
    
    async def selectCard(self, interaction: discord.Interaction):
        self.clear_items()
        embedIndex = int(float(self.selectMenu.values[0]))
        returnButton = discord.ui.Button(label="Return to Inventory")
        returnButton.callback = self.returnCallback
        self.add_item(returnButton)
        await interaction.response.edit_message(view=self, embed=self.embedList[embedIndex])

    #async def gallerySelectionCallback(self, interaction: discord.Interaction, button: discord.ui.Button):
    #    #self.clear_items() 
    #    returnButton = discord.ui.Button(label=f"Return to Inventory")
    #    returnButton.callback = self.returnCallback(self.pageIndex)
    #    await interaction.response.edit_message(embed=self.embedList[button.custom_id], view=self)
    
    # <varName> : <dataType> specification of the passed data type
    async def nextPageCallback(self, interaction: discord.Interaction, button: discord.ui.Button, forward):
        #self.clear_items() 
        if forward:
            self.pageIndex = (self.pageIndex + 1) % self.maxPageSize
        else:
            self.pageIndex = abs(self.pageIndex - 1) % self.maxPageSize
        self.assemblePage(self.pageIndex)
        await interaction.response.edit_message(content=f"Page: {self.pageIndex}",view=self)

async def loadViewParams(ctx,invDict):
    if len(invDict["CardIDs"]) == 0:
        await ctx.send("Unable to create inventoryView with empty inventory") 
        return -1, -1
    embedList = []
    optionList = []
    tempOptions = [] 
    index = 0
    for cardID in invDict["CardIDs"]: #assembling list of embeds 
        cardFound = await silentSearch(ctx,dbType.CARD_JSON,cardID)
        tempCardDict = json.loads(cardFound.content)
        cardEmbed = discord.Embed(title=tempCardDict["Title"], description=f"\nCard ID: {tempCardDict["CardID"]}\nCreated by: {tempCardDict["Creator"]}\nRarity: {tempCardDict["Rarity"]}")
        cardEmbed.set_image(url=tempCardDict["Content"])
        
        embedList.append(cardEmbed)
        option = discord.SelectOption(label=f"{tempCardDict["Title"]}", value=f"{index}", description=f"Rarity: {tempCardDict["Rarity"]} CardID: {tempCardDict["CardID"]}")
        tempOptions.append(option)
        if (index+1) % 25 == 0 or index == len(invDict["CardIDs"])-1: 
            print("Accessed page finalizer")
            optionList.append(list(tempOptions))
            tempOptions.clear()
        index += 1 
    print(f"Checking loadViewParams correctness: optionList size: {len(optionList)}\n")
    for mOption in optionList: 
        for option in mOption: 
            print(f"OPTION: label: {option.label} value: {option.value}")
        
    return embedList,optionList


async def dictToDisplay(ctx,type,dbDict): #only supports cards and users 
    if type.value == 1: #CARD 
        embed = discord.Embed(title=dbDict["Title"], description=f"\nCard ID: {dbDict["CardID"]}\nCreated by: {dbDict["Creator"]}\nRarity: {dbDict["Rarity"]}")
        embed.set_image(url=dbDict["Content"])
    if type.value == 2: #USER
        embed = discord.Embed(title=dbDict["Username"], description=f"\nInventory ID: {dbDict["InventoryID"]}\nBalance: {dbDict["Balance"]}")
    if type.value == 3: #INVENTORY
        #embedList, pageList, cardDicts = [], [], []
        embedList, optionList = [], []
        embedList, optionList = await loadViewParams(ctx, dbDict)
        if embedList == -1: 
            return -1
        print(f"dictToDisplay: ACCESSED INVENTORY {dbDict["InventoryID"]}")
        invView = inventoryView(embedList, optionList)
        return invView
        #await ctx.send(invView)
        #embed = discord.Embed(title=dbDict["Username"], description=f"\nInventory ID: {dbDict["InventoryID"]}\nBalance: {dbDict["Balance"]}")
    return embed

async def sendEmbedFromJson(ctx,type, jsonData: str): #TODO: renderEmbed needs to account for inventories and users 
    dbDict = json.loads(jsonData) #converts json string object to dict 
    if type.value == 1:
        dbEmbed = await dictToDisplay(ctx,dbType.CARD_JSON,dbDict)
    elif type.value == 2:  
        dbEmbed = await dictToDisplay(ctx,dbType.USER_JSON,dbDict)
    elif type.value == 3:
        dbView = await dictToDisplay(ctx,dbType.INVENTORY_JSON, dbDict)
        if dbView == -1: 
            return -1
        await ctx.send(view=dbView)
        return dbView 
        #inventory json-data to compose gallery 
        #await search(ctx,dbType.INVENTORY_JSON,jsonData["InventoryID"]).edit(embed=invEmbed)
    await ctx.send(embed=dbEmbed)
    return dbEmbed
    
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