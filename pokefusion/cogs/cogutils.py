from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from discord import Color, Embed, File

from pokefusion import imagelib
from pokefusion.assetmanager import AssetManager
from pokefusion.bot.context import Context, Reply
from pokefusion.fusionapi import FusionResult, Sprite
from pokefusion.imagelib import FilterType
from pokefusion.types import StrPath

type EmbedMedia = StrPath | File


@dataclass(frozen=True, slots=True)
class EmbedField:
    name: str
    value: str
    inline: bool = True


def _prepare_media(media: EmbedMedia | None, files: list[File]) -> str | None:
    if media is None:
        return None

    if isinstance(media, str):
        return media

    file = media if isinstance(media, File) else File(media)
    files.append(file)

    return f"attachment://{file.filename}"


def embed_factory(
        *,
        fields: Sequence[EmbedField] = (),
        image: EmbedMedia | None = None,
        thumbnail: EmbedMedia | None = None,
        footer_text: str | None = None,
        footer_icon: EmbedMedia | None = None,
        author_name: str | None = None,
        author_url: str | None = None,
        author_icon: EmbedMedia | None = None,
        **kwargs
) -> tuple[Embed, list[File]]:
    if footer_text is None and footer_icon is not None:
        raise ValueError("A footer icon requires footer text")

    if author_name is None and (author_url is not None or author_icon is not None):
        raise ValueError("An author URL or icon requires an author name")

    files = []

    image_url = _prepare_media(image, files)
    thumbnail_url = _prepare_media(thumbnail, files)
    footer_icon_url = _prepare_media(footer_icon, files)
    author_icon_url = _prepare_media(author_icon, files)

    embed = Embed(**kwargs)

    for field in fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)

    if image_url is not None:
        embed.set_image(url=image_url)

    if thumbnail_url is not None:
        embed.set_thumbnail(url=thumbnail_url)

    if footer_text is not None:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

    if author_name is not None:
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)

    return embed, files


def base_embed(ctx: Context, **kwargs) -> tuple[Embed, list[File]]:
    color = kwargs.pop("color", ctx.bot.main_color)
    return embed_factory(color=color, **kwargs)


def footer_embed(ctx: Context, **kwargs) -> tuple[Embed, list[File]]:
    return base_embed(ctx, footer_text=f"Requested by {ctx.author.display_name}", **kwargs)


def fusion_embed(ctx: Context, result: FusionResult, **kwargs) -> tuple[Embed, list[File]]:
    color = Color.from_rgb(*imagelib.get_dominant_color(result.path))
    head, body = result.head, result.body

    fields = (
        EmbedField("Head", f"{head.species} #{head.dex_id}" + ("\n\n🆕" if result.is_new else "")),
        EmbedField("Body", f"{body.species} #{body.dex_id}" + ("\n\n🆕" if result.swap().is_new else ""))
    )

    filename_fusions = f"fusions_{str(head.dex_id).zfill(3)}_{str(body.dex_id).zfill(3)}.png"
    combined_fusions = imagelib.merge_images(result.path, result.swap().path, pixel_gap=50, crop_bbox=True)
    fusions = File(combined_fusions, filename_fusions)

    filename_eggs = f"eggs_{str(head.dex_id).zfill(3)}_{str(body.dex_id).zfill(3)}.png"
    combined_eggs = imagelib.merge_images(result.egg_path, result.swap().egg_path, pixel_gap=5, crop_bbox=True)
    eggs = File(combined_eggs, filename_eggs)

    embed, files = footer_embed(
        ctx,
        color=color,
        fields=fields,
        image=fusions,
        thumbnail=eggs,
        **kwargs
    )

    return embed, files


def guess_fusion_embed(
        ctx: Context,
        result: FusionResult,
        filters: list[FilterType] | None = None,
        title: str = "Guess the fusion!"
) -> tuple[Embed, list[File]]:
    color = Color.from_rgb(*imagelib.get_dominant_color(result.path))
    fields = (EmbedField("Head", "?"), EmbedField("Body", "?"))

    filtered = result.path

    if filters:
        for filter_ in filters:
            filtered = imagelib.apply_filter(filtered, filter_type=filter_)

    image = File(filtered, "guess.png")

    embed, files = base_embed(
        ctx,
        title=title,
        color=color,
        fields=fields,
        image=image,
        footer_text="Type <Pokémon> <Pokémon>"
    )

    return embed, files


def guess_filter_embed(
        ctx: Context,
        filters: list[FilterType],
        sprite: Sprite,
        title: str = "Guess the Pokémon!"
) -> tuple[Embed, list[File]]:
    filtered = imagelib.apply_filter(sprite.path, filter_type=filters[0], scale=3)

    for filter_ in filters[1:]:
        filtered = imagelib.apply_filter(filtered, filter_type=filter_)

    image = File(filtered, "guess.png")

    embed, files = base_embed(
        ctx,
        title=title,
        image=image,
        footer_text="Type <Pokémon>"
    )

    return embed, files


def description_embed(ctx: Context, description: str, title: str = "Guess the Pokémon!") -> tuple[Embed, list[File]]:
    thumbnail = Path(AssetManager.MISC_DIR) / "Substitute.png"
    color = Color.from_rgb(*imagelib.get_dominant_color(thumbnail, normalize=True))

    embed, files = base_embed(
        ctx,
        title=title,
        description=description,
        color=color,
        thumbnail=thumbnail,
        footer="Type <Pokémon>"
    )

    return embed, files


def birthday_embed(ctx: Context, color: Color) -> tuple[Embed, list[File]]:
    embed, files = base_embed(
        ctx,
        title="Birthday event",
        color=color,
        thumbnail=Path(AssetManager.MISC_DIR) / "Substitute.png",
        description=f"Use `{ctx.prefix}bday` for free rerolls during your birthday!",
        footer_text=f"Happy birthday {ctx.author.display_name}!"
    )

    return embed, files


def christmas_embed(ctx: Context, color: Color) -> tuple[Embed, list[File]]:
    embed, files = base_embed(
        ctx,
        title="Christmas event",
        color=color,
        thumbnail=Path(AssetManager.MISC_DIR) / "ChristmasPresent.png",
        description=f"Use `{ctx.prefix}kdo` for free rerolls until January 1!",
        footer_text="Happy Holidays!"
    )

    return embed, files


async def guess_prompt(ctx: Context, description: str, delete: bool = False) -> Reply:
    thumbnail = Path(AssetManager.MISC_DIR) / "Unknown.png"
    color = Color.from_rgb(*imagelib.get_dominant_color(thumbnail, normalize=True))

    embed, files = base_embed(
        ctx,
        description=description,
        color=color,
        thumbnail=thumbnail,
        footer_text="Type yes or no."
    )

    message = await ctx.send(embed=embed, files=files)
    reply = await ctx.prompt(timeout=10, delete_reply=delete)

    if delete:
        await message.delete()

    return reply
