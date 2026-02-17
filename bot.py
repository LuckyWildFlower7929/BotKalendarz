import discord
from discord.ext import commands, tasks
import calendar
from datetime import datetime, timedelta
import asyncio
import aiosqlite
import os
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Kalendarz Bot działa! ✅"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CHANNEL_ID = 1472990294524952855  # Twoje ID

async def init_db():
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS tasks 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             user_id INTEGER, task TEXT, date TEXT, remind_min INTEGER)''')
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    print(f'{bot.user} gotowy!')
    check_reminders.start()

def generate_calendar():
    today = datetime.now()
    cal_text = calendar.month(today.year, today.month)
    day_str = f"[{today.day:2d}]"
    cal_highlighted = cal_text.replace(f' {today.day:2d} ', f' {day_str} ')
    lines = cal_highlighted.split('\n')  # POPRAWIONE
    framed = "┌" + "─" * 24 + "┐\n"
    for line in lines:
        framed += f"│{line[:24]:<24}│\n"
    framed += "└" + "─" * 24 + "┘"
    return f"```{framed}``` 📅 **{calendar.month_name[today.month]} {today.year}**"

@bot.command()
async def kalendarz(ctx):
    embed = discord.Embed(title="📆 Kalendarz", color=0x3498db)
    embed.add_field(name="Miesiąc", value=generate_calendar(), inline=False)
    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)

@bot.command()
async def zadania(ctx):
    async with aiosqlite.connect('tasks.db') as db:
        async with db.execute("SELECT id, task, date FROM tasks WHERE user_id=?", (ctx.author.id,)) as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await ctx.send("Brak zadań! ✅")
        return
    lista = "\n".join([f"`ID{row[0]}`: **{row[1]}** ({row[2]})" for row in rows])  # POPRAWIONE
    embed = discord.Embed(title="📝 Zadania", description=lista, color=0x9b59b6)
    await ctx.send(embed=embed)

@bot.command()
async def dodaj(ctx, date: str, *, task: str):
    mins = 60
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute("INSERT INTO tasks (user_id, task, date, remind_min) VALUES (?, ?, ?, ?)",
                         (ctx.author.id, task, date, mins))
        await db.commit()
    await ctx.send(f"✅ Dodano **{task}** na {date}")

@bot.command()
async def usun(ctx, task_id: int):
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, ctx.author.id))
        await db.commit()
    await ctx.send(f"🗑️ Usunięto ID {task_id}!")

@tasks.loop(minutes=1)
async def check_reminders():
    now = datetime.now()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return
    async with aiosqlite.connect('tasks.db') as db:
        async with db.execute("SELECT * FROM tasks") as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            task_date = datetime.strptime(row[3], '%Y-%m-%d')
            if now + timedelta(minutes=row[4]) >= task_date >= now:
                await channel.send(f"⏰ <@{row[1]}> **{row[2]}**!")
                await db.execute("DELETE FROM tasks WHERE id=?", (row[0],))
                await db.commit()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    # *** WKLEJ TUTAJ SWÓJ TOKEN Z DEVELOPER PORTAL ***
    TOKEN = "MTQ3MzE0MzQ1Mjg5OTQ3OTY1Mg.Gz32gT.0IxDW4qH_GTZoi1cM7m6iclPYW8m4LSpph2eGs"  # ← ZMIEŃ TO!
    bot.run(TOKEN)
