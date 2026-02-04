import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from typing import Annotated

from discord import Color, Embed, Member
from discord.ext import commands
from discord.ext.commands import CommandError, NotOwner

from pokefusion import utils
from pokefusion.assetmanager import AssetManager
from pokefusion.bot import PokeFusion
from pokefusion.context import Context, Reply
from pokefusion.converters import ModuleConverter
from .cogutils import AttachmentType, EmbedAttachment, embed_factory
from .scheduler import NOTIF_CHANNELS

logger = logging.getLogger(__name__)


class Owner(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot
        self.last_eval = None

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.is_owner().predicate(ctx)

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, NotOwner):
            await ctx.send("Owner only.")

    @commands.command(aliases=["mm"])
    async def maintenance(self, ctx: Context, new_state: bool | None = None) -> None:
        if new_state is None:
            current_state = self.bot.db.get_settings().maintenance_mode
            await ctx.send(f"Maintenance mode is {['off', 'on'][current_state]}.")
        else:
            self.bot.db.update_settings(params={"maintenance_mode": new_state})
            await ctx.send(f"Maintenance mode is now {['off', 'on'][new_state]}.")

    @commands.command(aliases=["rr"])
    async def reroll(self, ctx: Context, target: Member = None, delta: int = 1):
        target = target or ctx.author
        desc = f"Reroll {target.display_name}'s totem?"
        embed = Embed(description=desc, color=Color.light_grey())
        embed.set_footer(text="Type yes or no.")
        prompt = await ctx.send(embed=embed)
        reply = await ctx.prompt(timeout=10, delete_reply=True)

        if reply == Reply.NoReply:
            embed.set_footer(text=f"{ctx.author} didn't reply.")
        elif reply == Reply.No:
            embed.set_footer(text=f"{ctx.author} replied no.")
        else:
            embed.set_footer(text=f"{ctx.author} replied yes.")
            new_seed = self.bot.db.get_or_create_user(target).seed + delta
            self.bot.db.update_user(target, params={"seed": new_seed, "updated_at": datetime.now()})

        await prompt.edit(embed=embed)

    @commands.command(aliases=["rrg", "rr_global", "rerall"])
    async def reroll_global(self, ctx: Context, delta: int = 1):
        desc = f"Reroll **all** totems for **every** server?"
        embed = Embed(description=desc, color=Color.light_grey())
        embed.set_footer(text="Type yes or no.")
        prompt = await ctx.send(embed=embed)
        reply = await ctx.prompt(timeout=10, delete_reply=True)

        if reply == Reply.NoReply:
            embed.set_footer(text=f"{ctx.author} didn't reply.")
        elif reply == Reply.No:
            embed.set_footer(text=f"{ctx.author} replied no.")
        else:
            embed.set_footer(text=f"{ctx.author} replied yes.")
            new_seed = self.bot.db.get_settings().global_seed + delta
            self.bot.db.update_settings(params={"global_seed": new_seed, "updated_at": datetime.now()})

        await prompt.edit(embed=embed)

    @commands.command(aliases=["give_fr"])
    async def give_freererolls(self, ctx: Context, amount: int = 1, target: Member = None):
        desc = f"Give free reroll(s) to **everyone**?" if target is None else f"Give free reroll(s) to **{target.display_name}**?"
        embed = Embed(description=desc, color=Color.light_grey())
        embed.set_footer(text="Type yes or no.")
        prompt = await ctx.send(embed=embed)
        reply = await ctx.prompt(timeout=10, delete_reply=True)

        if reply == Reply.NoReply:
            embed.set_footer(text=f"{ctx.author} didn't reply.")
        elif reply == Reply.No:
            embed.set_footer(text=f"{ctx.author} replied no.")
        else:
            embed.set_footer(text=f"{ctx.author} replied yes.")
            self.bot.db.update_freererolls(target, amount)

        await prompt.edit(embed=embed)

    @commands.command(aliases=["spu"])
    async def sprite_pack_update(self, ctx: Context, free_rerolls: int = 0) -> None:
        warning = "The following embed will be sent to **all** notification subscribers, are you sure?"
        embed = Embed(description=warning, color=ctx.bot.main_color)
        embed.set_footer(text="Type yes or no.")
        prompt = await ctx.send(embed=embed)
        embed.set_footer(text=f"{ctx.author} replied yes.")

        title = "Sprite Pack Update"
        description = (
            "The latest sprite pack was imported:"
            ""
            "```asciidoc\n"
            "Sprite pack :: 121_December_2025\n"
            "Timestamp   :: 2026-02-05 00:05:00\n"
            "Changes     :: +2234/-23 custom fusions\n"
            "```\n"
        )
        if free_rerolls > 0:
            plural = "s" if free_rerolls > 1 else ""
            description += f"⚠️ All Totems had to be reset️. To compensate, everyone got **+{free_rerolls} free reroll{plural}**! Check how many you have with `{ctx.prefix}fru`"
        avatar = EmbedAttachment(AssetManager.get_avatar_path(self.bot.config.env), "avatar.png",
                                 AttachmentType.THUMBNAIL)
        preview, files = embed_factory(title=title, description=description, attachments=(avatar,),
                                       color=ctx.bot.main_color)
        await ctx.send(embed=preview, files=files)

        reply = await ctx.prompt(timeout=20)
        if reply == Reply.NoReply:
            embed.set_footer(text=f"{ctx.author} didn't reply.")
        elif reply == Reply.No:
            embed.set_footer(text=f"{ctx.author} replied no.")
        else:
            embed.set_footer(text=f"{ctx.author} replied yes.")
            for channel_id in NOTIF_CHANNELS:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed, files = embed_factory(title=title, description=description, attachments=(avatar,),
                                                 color=ctx.bot.main_color)
                    await channel.send(embed=embed, files=files)
        await prompt.edit(embed=embed)

    @commands.command()
    async def say(self, ctx: Context, *, message: str) -> None:
        await ctx.send(message)

    @commands.command()
    async def load(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command()
    async def unload(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command()
    async def reload(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command(aliases=["eval"])
    async def sudo(self, ctx: Context, *, body: str) -> None:
        env = {
            "self": self,
            "bot": self.bot,
            "db": self.bot.db,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self.last_eval
        }

        env.update(globals())

        body = utils.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f"async def _eval():\n{textwrap.indent(body, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.safe_send(f"```py\n{e.__class__.__name__}: {e}\n```")
            return

        func = env["_eval"]
        # noinspection PyBroadException
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            logger.error(traceback.format_exc())
            await ctx.safe_send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            await ctx.tick(True)

            if ret is None:
                if value:
                    await ctx.safe_send(f"```py\n{value}\n```")
            else:
                self.last_eval = ret
                await ctx.safe_send(f"```py\n{value}{ret}\n```")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Owner(bot))
