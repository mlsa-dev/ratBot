# ratBot.py
# Uses MySQL to record teamkills from players of Escape From Tarkov.
# It is genereic and can be tweaked to whichever game needed by changing database traits.
# author@ josh Priest
# github@ a1sauc
from datetime import datetime
import os
import logging as log
import random
from time import time
from typing import List
import discord
from dotenv import load_dotenv
from mysql.connector import connect, Error
from discord.ext import commands, tasks


try:
    logfile = os.environ.get('RATBOT.log', '/var/log/ratbot.log')
    logformat = os.environ.get('RATBOT_LOG_FORMAT', '%(asctime)s %(user)-8s %(message)s')
    log.basicConfig(filename=logfile,format=logformat)
except Exception as e:
    log.basicConfig(filename='RATBOT.log', level=log.DEBUG)
    log.error(f"time = {datetime.now()} \n error = {e}")
    print(e)

log.getLogger('discord').setLevel(log.ERROR)
log.getLogger('discord.client').setLevel(log.ERROR)
log.getLogger('discord.gateway').setLevel(log.ERROR)
log.getLogger('src').setLevel(log.ERROR)
log.getLogger('venv').setLevel(log.ERROR)


load_dotenv()
TOKEN = os.getenv("RATBOT_DISCORD_TOKEN")
userName = os.getenv("RATBOT_DB_USERNAME")
pw = os.getenv("RATBOT_DB_PW")
dbName = os.getenv("RATBOT_DB_NAME")
dbHost = os.getenv("RATBOT_DB_HOST")
intents = discord.Intents.default()
intents.members=True
#testing messages - delete line below later
intents.messages=True
bot = commands.Bot(command_prefix="$",help_command=None, intents=intents)

random.seed(a=None,version=2)

create_player_table = """ 
CREATE TABLE IF NOT EXISTS players (
    name VARCHAR(25),
    num_teamkills INT,
    num_victim INT
) 
"""
# DATE must be year-month-date 0000-00-00 for MySQL
# TIME can be hh:mm:ss
create_teamkill_table = """
CREATE TABLE IF NOT EXISTS teamkills (
    id VARCHAR(5),
    date DATE,
    killer VARCHAR(25),
    victim VARCHAR(25),
    map VARCHAR(15),
    weapon VARCHAR(15)
)
"""

global db_cursor
global db


print("Trying to connect to db server...")
try:
    db = connect(
        host=dbHost,
        user=userName,
        password=pw,
        database=dbName
    )
    db_cursor = db.cursor(buffered=True)
    log.info(f"Object type of db = {type(db)}")
    log.info(f"Object type of db_cursor = {type(db_cursor)}")

    print(f"Object type of db = {type(db)}")
    print(f"Object type of db_cursor = {type(db_cursor)}")
    db_cursor.execute(create_player_table)
    db_cursor.execute(create_teamkill_table)
    db.commit()
    print('Successful Database connection!')
except Error as e:
    log.critical("Error with database connection.")
    print(e)


# helper function to get player count
def getCount():
    
    cnt_qry = """
    SELECT COUNT(*) FROM players
    """
    results = db_cursor.execute(cnt_qry)
    #x = len(results)
    x = db_cursor.fetchall()
    return len(x)
    

# helper function to reconnect to database & create new cursor
def reconnection():
    try:
        db = connect(
            host=dbHost,
            user=userName,
            password=pw,
            database=dbName
        )
        db_cursor = db.cursor(buffered=True)
    except Error as e:
        log.error(e)
        # print to servers bot is going offline for maintenance
        #add system exit to kill bot 


# helper function to generate a random 5-digit ID # for an inserted kill
def genID():
    num = str(random.random())
    testNum = num[5:15:2]
    return testNum


# helper function for help command. Returns y as default if x is not found.
def findFunc(x):
    return {
        'addplayer':"[Command]\n\tCorrect format: $addplayer <playerName>\n\tAdds a new player to the records. Can only add one player at a time.\n",
        'getplayer':"[Command]\n\tCorrect format: $getplayer <playerName>\n\tGets a player's statistics Can only get one player at a time.\n",
        'deleteplayer':"[Command]\n\tCorrect format: $deleteplayer <Name>\n\tDeletes a player from the records. Can only delete one player at a time.\n",
        'addkill':"[Command]\n\tCorrect format: $addkill <killer> <victim> <map> <weapon>\n\tMap and weapon are optional but both are required if used.\n",
        'deletekill':"[Command]\n\tCorrect format: $deletekill <Id>\n\tDeletes a kill from the records. Id is a unique 5-digit number.\n",
        'showkills':"[Command]\n\tCorrect format: $showkills\n\tShows all the kills from the records\n",
        'showplayers':"[Command]\n\tCorrect format: $showplayers\n\tShows all the players and their statistics\n",
        'leaderboard':"[Command]\n\tCorrect format: $leaderboard\m\tRanks the players by most team kills\n",
        'help':"[Command]\n\tCorrect format: $help <command>\n\tShows the help screen message. Command is optional but will provide more detail if included.\n",
        'y':"Error! The inputted command is not in the list.\n"
    }.get(x,'y')

# Function for when bot is first turned on
# Output: Server side
@bot.event
async def on_ready():
    print(f'\n{bot.user.name} has connected to discord!')
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    print("time:", time)
    pass

@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    # Replace MissingRequiredArguments with your error
    await ctx.send("Input Error! {}.".format(error.args[0]))

# Prints guilds & members of each guild that ratBot is connected to (owner use)
# Output: server side
@bot.command()
async def getGuilds(ctx):
    guilds = bot.guilds
    print(f'\nServers I am connected to:')
    j = 1
    for i in guilds:
        print(f'{j}. {i}')
        print(f'Users:')
        j += 1
        k = 1
        members = await discord.guild.Guild.fetch_members(self=i,limit=150).flatten()
        for x in members:
            print(f'\t{k}. {x}')
            k += 1
            
        print('\n')
        

# format: $addPlayer <playerName>
# adds a new player to the database
# Output: client side
@bot.command()
async def addplayer(ctx, *args):
    
    if args.__len__() == 0 or args.__len__() > 1:
        await ctx.send("```Input Error! Correct format = $addplayer <name>```")

    else:
        
        newPlayer = args[0]

        db_np_query = """
        SELECT * FROM players WHERE name = %s
        """
        db_cursor.execute(db_np_query,(newPlayer,))

        records = db_cursor.fetchall()
        if len(records) < 1:
            # There are no records under inputted player name (Which we want) so create a new entry
            qry = """ INSERT INTO players (name, num_teamkills, num_victim) VALUES (%s, %s, %s) """
            val = (newPlayer, 0, 0)
            db_cursor.execute(qry, val)
            db.commit()
            if db_cursor.rowcount > 0:
                await ctx.send("```Successful insert. {} was added to the list```".format(newPlayer))    
            else:
                log.error("error when adding newPlayer")
        else:
            await ctx.send('```There are already records under that name, Insert new name```')


# format: $getplayer <Name>
# Gets a players' stats from table players
# Output: client side 
@bot.command()
async def getplayer(ctx, *args):
    
    if len(args) < 1 or len(args) > 1:
        await ctx.send('```Input Error! Correct format: $getplayer <playerName>```')
    else: 
        playerName = args[0]
        qry = """SELECT * FROM players WHERE name = %s"""
        db_cursor.execute(qry, (playerName,))
        ans = db_cursor.fetchall()
        if len(ans) > 0:    
            printName = ans[0][0]
            printKills = ans[0][1]
            printDeaths = ans[0][2]
            printStr = (f"```  Name         Teammate Kills        Deaths By Teammate\n" + 
                        "--------------------------------------------------------------\n" +
                        "  {:<20} {:<20} {:<20} ```".format(printName,printKills, printDeaths)
                        )
            await ctx.send(printStr)
        else:
            await ctx.send("```Player is not in the records. Try again with a new name```")


# format: $addkill <killer> <victim> <map> <weapon>
# IF no map and weapon, fill in with N/A
# increment killer & victim's stats in players table & add kill to teamkills table
# Output: client side
@bot.command()
async def addkill(ctx, *args):
    
    if len(args) != 2 and len(args) != 4:
        await ctx.send('```Input Error! Map and weapon are optional but both are required if used.\n Correct format: $addkill <killer> <victim> <map> <weapon>```')
    else:
        # map & weapon are included
        if len(args) > 2:
            killer = args[0]
            victim = args[1]
            map = args[2]
            weapon = args[3]
        else:
            killer = args[0]
            victim = args[1]
            map = 'N/a'
            weapon = 'N/a'
        
        # increment killer's teamKill stats in players table
        killerQry = """
        SELECT DISTINCT num_teamkills FROM players WHERE name = %s
        """
        db_cursor.execute(killerQry, (killer,))
        killerResults = db_cursor.fetchall()
        
        # increment vimctim's teamDeath stats in players table
        victimQry = """
        SELECT DISTINCT num_victim FROM players WHERE name = %s
        """
        db_cursor.execute(victimQry, (victim,))
        victimResults = db_cursor.fetchall()
        
        if len(killerResults) > 0 and len(victimResults) > 0:
            kills = killerResults[0][0]
            kills += 1
            updateKiller = """
            UPDATE players SET num_teamkills = %s WHERE name = %s 
            """
            db_cursor.execute(updateKiller, (kills, killer))
            if db_cursor.rowcount < 1:
                log.error("Error while incrementing killer's teamkills")
            
            deaths = victimResults[0][0]
            deaths += 1
            updateVictim = """
            UPDATE players SET num_victim = %s WHERE name = %s
            """
            db_cursor.execute(updateVictim, (deaths, victim))
            if db_cursor.rowcount < 1:
                log.error("Error while incrementing victim's deaths")
            db.commit()

            # Update teamkills table with confirmed kill
            # DATE must be year-month-date 0000-00-00
            # rjust to pad numbers with a 0 if number is less than 10 and has a single digit 
            date = ctx.message.created_at.date()
            time = ctx.message.created_at.now()
            hr = str(time.hour).rjust(2,"0")
            min = str(time.minute).rjust(2,"0")
            sec = str(time.second).rjust(2,"0")
            printTime = '{}:{}:{}'.format(hr,min,sec)        
            
            id = genID()
            
            cntQry = """
            SELECT COUNT(*) FROM teamkills
            """
            db_cursor.execute(cntQry)
            ans = db_cursor.fetchall()
            if len(ans) > 1:
                
                idQry = """
                SELECT * FROM teamkills WHERE id = %s
                """
                db_cursor.execute(idQry,(id,))
                res = db_cursor.fetchall()
                if len(res) > 0:
                    # ID is in list so regenerate ID
                    id = genID()
                    db_cursor.execute(idQry,(id,))
                    result = db_cursor.fetchall()
                    while len(result) > 0:
                        id = genID()
                        # newly generated ID
                        db_cursor.execute(idQry,(id,))
                        result = db_cursor.fetchall()

            

            killQry = """
            INSERT INTO teamkills (id, date, killer, victim, map, weapon) VALUES (%s, %s, %s, %s, %s, %s) 
            """
            val = (id, date, killer, victim, map, weapon)
            db_cursor.execute(killQry,val)
            if db_cursor.rowcount < 1:
                log.error("Error while adding kill to table teamkill")
            db.commit()
            await ctx.send('```Kill was added to the records.```')
        else:
            #killer or victim is not in database
            if len(killerResults) < 1 and len(victimResults) < 1:
                await ctx.send('```{} and {} are not in the records. Try again.```'.format(killer,victim))
            elif len(victimResults) < 1:
                await ctx.send('```{} is not in the records. Try again.```'.format(victim))
            else:
                await ctx.send('```{} is not in the records. Try again.```'.format(killer))       
        pass

# format: $deletekill <Id>
# Output: client side
@bot.command()
async def deletekill(ctx, *args):
    
    if len(args) == 0:
        await ctx.send('```Input error! Please enter a kill Id # to delete. Correct format: $deletekill <Id>```')
    elif len(args) > 1:
        await ctx.send('```Input error! Can only delete 1 kill at a time. Correct format: $deletekill <Id>```')
    else:
        delID = str(args[0])
        srchQry = """
        SELECT * FROM teamkills WHERE id = %s
        """
        db_cursor.execute(srchQry,(delID,))
        res = db_cursor.fetchall()
        if len(res) < 1:
            await ctx.send('```Delete failed. Kill id:{} was not in the records```'.format(delID))
        else:
            #Deletes kill from teamKills & decrements Killer's kills & Victim's deaths stats in players table
            delQry = """
            DELETE FROM teamkills where id = %s
            """
            db_cursor.execute(delQry,(delID,))

            #res[2] = killer, res[3] = victim
            killer = res[0][2]
            victim = res[0][3]
            # deincrement killer's teamKill stats in players table
            killerQry = """
            SELECT DISTINCT num_teamkills FROM players WHERE name = %s
            """
            db_cursor.execute(killerQry, (killer,))
            killerResults = db_cursor.fetchall()
            
            # deincrement vimctim's teamDeath stats in players table
            victimQry = """
            SELECT DISTINCT num_victim FROM players WHERE name = %s
            """
            db_cursor.execute(victimQry, (victim,))
            victimResults = db_cursor.fetchall()
            
            if len(killerResults) > 0 and len(victimResults) > 0:
                kills = killerResults[0][0]
                kills -= 1
                updateKiller = """
                UPDATE players SET num_teamkills = %s WHERE name = %s 
                """
                db_cursor.execute(updateKiller, (kills, killer))
                
                deaths = victimResults[0][0]
                deaths -= 1
                updateVictim = """
                UPDATE players SET num_victim = %s WHERE name = %s
                """
                db_cursor.execute(updateVictim, (deaths, victim))

            db.commit()
            await ctx.send('```Delete sucessful! Kill id:{} was removed from the table```'.format(delID))
    pass


# format: $deleteplayer
# note in help command that can only delete 1 player 
# Output: client side
@bot.command()
async def deleteplayer(ctx, *args):
    
    if len(args) == 0:
        await ctx.send('```Input error! Please enter a name. Correct format: $deleteplayer <Name>```')
    elif len(args) > 1:
        await ctx.send('```Input error! Can only delete one player at a time```')
    else:
        delPlayer = args[0]
        srchQry = """
        SELECT * FROM players WHERE name = %s
        """
        db_cursor.execute(srchQry,(delPlayer,))
        res = db_cursor.fetchall()

        if len(res) < 1:
            await ctx.send('```Input error! {} was not in the database```'.format(delPlayer))
        else:
            delQry = """
            DELETE FROM players where name = %s 
            """
            db_cursor.execute(delQry,(delPlayer,))
            db.commit()
            await ctx.send('```Delete Sucessful! {} was removed from the records```'.format(delPlayer))
    pass


# format: $showkills
# Grabs all data from teamkills Table & outputs to discord
# Output: client side
@bot.command()
async def showkills(ctx):
    
    qry = """
    SELECT * FROM teamkills
    """
    db_cursor.execute(qry)
    results = db_cursor.fetchall()
    s = "```  {:<10}{:<10}{:<12}{:<12}{:<12}{:<12}\n{:-<67}\n".format("ID","Date","Killer","Victim","Map", "Weapon","-")
    x = 0
    for i in results:
        id = results[x][0]
        date = results[x][1]
        killer = results[x][2]
        victim = results[x][3]
        map = results[x][4]
        weapon = results[x][5]
        strDate = str(date)
        addString = f" {id:<{8}}{strDate:<13}{killer:<12}{victim:<12}{map:<13}{weapon:<13}\n"
        s += addString
        x += 1
    s += "```"
    await ctx.send(s)

    
# format: $showplayers
# Grabs all data from players Table & outputs to discord
# Output: client side
@bot.command()
async def showplayers(ctx):
    
    qry = """
    SELECT * FROM players
    """
    db_cursor.execute(qry)
    results = db_cursor.fetchall()
    s = "```  {:<20}{:<23}{:<15}\n{:-<67}\n".format("Name","Team Kills","Deaths By Teammates","-")

    for row in results:
        name = row[0]
        kills = row[1]
        deaths = row[2]

        s = s + "  {:<23} {:<27} {:<20} ".format(name,kills,deaths) + '\n'
    s += "```"
    await ctx.send(s)


# Help command to describe what each ratBot's function's do
# Correct format: $help or $help <command> for a more info about command
# Output: Client side
@bot.command()
async def help(ctx, *args):

    if len(args) < 1:
        s = """```Commands:
        addplayer       - adds a new player to the records
        getplayer       - gets a player's statistics
        deleteplayer    - deletes a player from the records
        addkill         - adds a kill to the records
        deletekill      - deletes a kill from the records
        showkills       - shows all the kills
        showplayers     - shows all the players & their statistics
        leaderboard     - ranks the players by most team kills
        help            - show this message

        Type $help <command> for more info on a command.```
        """
        await ctx.send(s)
    elif len(args) == 1:
        # use ``` Before & after sentence to format into code block on discord
        s = "```"
        s += findFunc(args[0])
        s += "```"
        await ctx.send(s)
    else:
        await ctx.send("```Input Error! Correct format: $help <command>\t\tThe command is optional\n```")


# Shows a leaderboard that ranks players by most team kills
# Output: client side
@bot.command()
async def leaderboard(ctx):
    
    print('leaderboard')
    sql = "SELECT * FROM players ORDER BY num_teamkills DESC"
    db_cursor.execute(sql)
    res = db_cursor.fetchall()
    if len(res) < 1:
        await ctx.send("There are no players in the records")
    else:
        s = """```
          Team Kills        Deaths By Team            Rat
        ---------------------------------------------------
        """
        z = 0
        for i in res:
            s += """       {}        │         {}           │       {}       \n\t\t""".format(res[z][1],res[z][2],res[z][0])
            z += 1
        s += "```"
        await ctx.send(s)


# Testing purposes - prints info about databases & tables
# Output: server side
'''
db_cursor.execute("show databases")
res = db_cursor.fetchall()
for i in res:
    print(i)

db_cursor.execute("SHOW TABLES FROM rat_stats")
res = db_cursor.fetchall()
for i in res:
    print(i)

print('TESTING teamkills')
db_cursor.execute("DESCRIBE teamkills")
results = db_cursor.fetchall()
for row in results:
    print(row)

print('TESTING players')
db_cursor.execute("DESCRIBE players")
results = db_cursor.fetchall()
for row in results:
    print(row)
'''

# Testing purposes - Delete both tables in rat_stats database
# Output: server side
@bot.command()
async def deleteTables(ctx):
    qry = "drop table players"
    db_cursor.execute(qry)
    qry = "drop table teamkills"
    db_cursor.execute(qry)
    db.commit()
    db_cursor.close()
    db.close()
    print('Delete sucessful!')
    exit(0)

# task to ping server to keep pipe to database from breaking (timeout = 10min)
@tasks.loop(minutes=9)
async def ping_server():
    db.ping()


ping_server.start()
bot.run(TOKEN)