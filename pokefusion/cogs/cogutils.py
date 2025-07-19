import os
from enum import Enum, IntEnum, auto
from typing import Any, NamedTuple

from discord import Color, Embed, File

from pokefusion import imagelib
from pokefusion.assetmanager import AssetManager
from pokefusion.context import Context, Reply
from pokefusion.fusionapi import FusionResult, Sprite
from pokefusion.imagelib import FilterType, PathOrBytes


class WeekDay(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class AttachmentType(Enum):
    IMAGE = auto()
    THUMBNAIL = auto()
    FOOTER = auto()
    AUTHOR = auto()
    DEFAULT = IMAGE


class EmbedField(NamedTuple):
    name: Any = None
    value: Any = None
    inline: bool = True


class EmbedAttachment(NamedTuple):
    fp: PathOrBytes
    filename: str
    type: AttachmentType = AttachmentType.DEFAULT


class EmbedFooter(NamedTuple):
    text: Any = None
    icon_url: Any = None


class EmbedThumbnail(NamedTuple):
    url: Any = None


class EmbedAuthor(NamedTuple):
    name: Any
    url: Any = None
    icon_url: Any = None


def embed_factory(*, fields: tuple[EmbedField, ...] = (), attachments: tuple[EmbedAttachment, ...] = (),
                  footer: EmbedFooter = None, thumbnail: EmbedThumbnail = None, author: EmbedAuthor = None,
                  **kwargs, ) -> tuple[Embed, list[File]]:
    embed = Embed(**kwargs)
    files = []
    for field in fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    if footer:
        embed.set_footer(text=footer.text, icon_url=footer.icon_url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail.url)
    if author:
        embed.set_author(name=author.name, url=author.url, icon_url=author.icon_url)
    for attachment in attachments:
        file = File(fp=attachment.fp, filename=attachment.filename)
        files.append(file)
        url = f"attachment://{file.filename}"
        if attachment.type == AttachmentType.IMAGE:
            embed.set_image(url=url)
        elif attachment.type == AttachmentType.THUMBNAIL:
            embed.set_thumbnail(url=url)
        elif attachment.type == AttachmentType.FOOTER:
            embed.set_footer(text=footer.text if footer else None, icon_url=url)
        else:  # AUTHOR
            embed.set_author(name=author.name, url=author.url, icon_url=url)
    return embed, files


def base_embed(ctx: Context, **kwargs) -> tuple[Embed, list[File]]:
    color = kwargs.pop("color", ctx.bot.main_color)
    return embed_factory(color=color, **kwargs)


def footer_embed(ctx: Context, **kwargs) -> tuple[Embed, list[File]]:
    return base_embed(ctx, footer=EmbedFooter(f"Requested by {ctx.author.display_name}"), **kwargs)


def fusion_embed(ctx: Context, result: FusionResult, **kwargs) -> tuple[Embed, list[File]]:
    color = Color.from_rgb(*imagelib.get_dominant_color(result.path))
    head, body = result.head, result.body
    filename_fusions = f"fusions_{str(head.dex_id).zfill(3)}_{str(body.dex_id).zfill(3)}.png"
    filename_eggs = f"eggs_{str(head.dex_id).zfill(3)}_{str(body.dex_id).zfill(3)}.png"
    combined_fusions = imagelib.merge_images(result.path, result.swap().path, pixel_gap=50, crop_bbox=True)
    combined_eggs = imagelib.merge_images(result.egg_path, result.swap().egg_path, pixel_gap=5, crop_bbox=True)
    fusions = EmbedAttachment(fp=combined_fusions, filename=filename_fusions, type=AttachmentType.IMAGE)
    eggs = EmbedAttachment(fp=combined_eggs, filename=filename_eggs, type=AttachmentType.THUMBNAIL)
    head_text = f"{result.head.species} #{result.head.dex_id}" + ("\n\n🆕" if result.is_new else "")
    body_text = f"{result.body.species} #{result.body.dex_id}" + ("\n\n🆕" if result.swap().is_new else "")
    fields = (EmbedField("Head", head_text), EmbedField("Body", body_text))
    return footer_embed(ctx, color=color, fields=fields, attachments=(fusions, eggs), **kwargs)


def guess_fusion_embed(ctx: Context, result: FusionResult, title: str = "Devine la fusion !") -> tuple[
    Embed, list[File]]:
    color = Color.from_rgb(*imagelib.get_dominant_color(result.path))
    # combined = imagelib.merge_images(result.path, result.swap().path, pixel_gap=50, crop_bbox=True)
    fusion = EmbedAttachment(fp=result.path, filename="guess.png", type=AttachmentType.IMAGE)
    fields = (EmbedField("Head", "?"), EmbedField("Body", "?"))
    return footer_embed(ctx, title=title, color=color, fields=fields, attachments=(fusion,))


def guess_filter_embed(ctx: Context, filters: list[FilterType], sprite: Sprite, title: str = "Devine le Pokémon !") -> \
        tuple[Embed, list[File]]:
    silhouette = imagelib.apply_filter(sprite.path, filter_type=filters[0], scale=3)

    for filter_ in filters[1:]:
        silhouette = imagelib.apply_filter(silhouette, filter_type=filter_)

    attachment = EmbedAttachment(silhouette, "guess.png", AttachmentType.IMAGE)
    return footer_embed(ctx, title=title, attachments=(attachment,))


def description_embed(ctx: Context, description: str, title: str = "Devine le Pokémon !") -> tuple[Embed, list[File]]:
    attachment = EmbedAttachment(os.path.join(AssetManager.MISC_DIR, "Substitute.png"), "Substitute.png",
                                 AttachmentType.THUMBNAIL)
    color = AssetManager.get_asset_color(attachment.fp)
    return footer_embed(ctx, title=title, description=description, color=color, attachments=(attachment,))


def birthday_embed(ctx: Context, color: Color, upload_attachment: bool = True) -> tuple[Embed, list[File]]:
    if upload_attachment:
        attachments = (
            EmbedAttachment(os.path.join(AssetManager.MISC_DIR, "BirthdayPresent.png"), "BirthdayPresent.png",
                            AttachmentType.THUMBNAIL),)
    else:
        attachments = ()
    footer = EmbedFooter(f"Happy birthday {ctx.author.display_name}!")
    return base_embed(ctx, title="Birthday event", description="Use !bday for free rerolls during your birthday!",
                      footer=footer, color=color, attachments=attachments)


def christmas_embed(ctx: Context, color: Color, upload_attachment: bool = True) -> tuple[Embed, list[File]]:
    if upload_attachment:
        attachments = (
            EmbedAttachment(os.path.join(AssetManager.MISC_DIR, "ChristmasPresent.png"), "ChristmasPresent.png",
                            AttachmentType.THUMBNAIL),)
    else:
        attachments = ()
    footer = EmbedFooter(f"Happy Holidays!")
    return base_embed(ctx, title="Christmas event", description="Use !kdo for free rerolls until January 1!",
                      footer=footer, color=color, attachments=attachments)


async def guess_prompt(ctx: Context, description: str, delete: bool = False) -> Reply:
    attachment = EmbedAttachment(os.path.join(AssetManager.MISC_DIR, "Unknown.png"), "Unknown.png",
                                 AttachmentType.THUMBNAIL)
    color = AssetManager.get_asset_color(attachment.fp)
    footer = EmbedFooter("Type yes or no.")
    embed, files = base_embed(ctx, description=description, color=color, footer=footer, attachments=(attachment,))
    prompt = await ctx.send(embed=embed, files=files)
    reply = await ctx.prompt(timeout=10, delete_reply=delete)

    if delete:
        await prompt.delete()

    return reply
