import asyncio
import json

import discord
from discord.colour import Color
from discord.ext import commands

import utils

bot = commands.Bot(command_prefix="!")
with open("data/pokedex.json", "r", encoding="utf-8") as f:
    raw = json.load(f)
normalized = {key: utils.normalize(value) for key, value in raw.items()}
POKEDEX = utils.TwoWayDict(normalized)
LAST_QUERIES = {}


@bot.command()
async def debug(ctx, *expr):
    if ctx.author.id == 92469090249089024:
        await ctx.send(eval(" ".join(expr)))
    else:
        await ctx.send("**Nice try**")


@bot.command(aliases=["Fusion", "f", "F"])
async def fusion(ctx, head="random", body="random"):
    global last_head, last_body
    try:
        head_id, head = utils.resolve(head, POKEDEX)
        body_id, body = utils.resolve(body, POKEDEX)
    except KeyError:
        return
    LAST_QUERIES[ctx.message.channel] = head, body
    url = f"http://images.alexonsager.net/pokemon/fused/{body_id}/{body_id}.{head_id}.png"
    color = Color(utils.get_dominant_color(url))
    embed = discord.Embed(title="PokéFusion", url="https://fr.pokemon.alexonsager.net/", color=color)
    embed.add_field(name="Head", value=head.title(), inline=True)
    embed.add_field(name="Body", value=body.title(), inline=True)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


@bot.command(aliases=["Swap", "s", "S"])
async def swap(ctx):
    if ctx.channel in LAST_QUERIES:
        head, body = LAST_QUERIES[ctx.channel]
        await ctx.invoke(fusion, head=body, body=head)


@bot.command(aliases=["Pokemon", "p", "P"])
async def pokemon(ctx, pkmn="random"):
    dex_num, pkmn = utils.resolve(pkmn)
    url = f"http://images.alexonsager.net/pokemon/{dex_num}.png"
    color = Color(utils.get_dominant_color(url))
    embed = discord.Embed(title=pkmn.title(), color=color)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


@bot.command()
async def clear(ctx, amount: int = 5):
    counter = 0
    async for m in ctx.channel.history().filter(lambda m: m.author == bot.user):
        if counter < amount:
            await m.delete()
            await asyncio.sleep(0.15)
            counter += 1


@bot.command()
async def changelog(ctx):
    changelog = f"```md\n{utils.get_changelog()}\n```"
    await ctx.send(changelog)


@bot.event
async def on_ready():
    print("Successfully logged in as {0} (ID {0.id})".format(bot.user))


bot.run(utils.get_token())
