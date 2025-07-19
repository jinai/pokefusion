from enum import Enum, auto
from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageFilter

type RGB = tuple[int, int, int]
type RGBA = tuple[int, int, int, int]
type PathOrBytes = str | BinaryIO


class Orientation(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()
    DEFAULT = HORIZONTAL


class FilterType(Enum):
    SILHOUETTE = auto()
    GAUSSIAN_BLUR = auto()
    PIXELATE = auto()
    DEFAULT = SILHOUETTE


def get_dominant_color(image: PathOrBytes, normalize: bool = False) -> RGB:
    if normalize:
        image = normalize_image(image)

    base = Image.open(image)
    if base.mode != "RGBA":
        base = base.convert("RGBA")

    w, h = base.size
    colors = base.getcolors(w * h)
    dominant = colors[0]

    for count, color in colors:
        cmax, cmin = max(color[:3]), min(color[:3])
        lightness = (cmax + cmin) / 2
        if lightness > 51 and count > dominant[0]:
            # Discard transparent & dark pixels (lightness < 20%)
            dominant = (count, color)

    r, g, b, _ = dominant[1]

    return r, g, b


def zoom_image(image: PathOrBytes, factor: int = 2) -> BytesIO:
    base = Image.open(image)
    zoomed = base.resize(tuple(int(factor * x) for x in base.size), resample=Image.Resampling.NEAREST)

    buffer = BytesIO()
    zoomed.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def pad_image(image: PathOrBytes) -> BytesIO:
    base = Image.open(image)
    old_width, old_height = base.size
    new_width, new_height = old_width + 100, old_height + 100

    padded = Image.new("RGBA", (new_width, new_height))
    padded.paste(base, ((new_width - old_width) // 2, (new_height - old_height) // 2))

    buffer = BytesIO()
    padded.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def merge_images(image1: PathOrBytes, image2: PathOrBytes, orientation: Orientation = Orientation.DEFAULT,
                 pixel_gap: int = 2, crop_bbox: bool = True) -> BytesIO:
    image1 = normalize_image(image1, crop_bbox=crop_bbox)
    image2 = normalize_image(image2, crop_bbox=crop_bbox)

    image1 = Image.open(image1)
    image2 = Image.open(image2)

    if orientation is Orientation.HORIZONTAL:
        size = (image1.width + image2.width + pixel_gap, max(image1.height, image2.height))
        offset = (image1.width + pixel_gap, 0)
    else:
        size = (max(image1.width, image2.width), image1.height + image2.height + pixel_gap)
        offset = (0, image1.height + pixel_gap)

    merged = Image.new("RGBA", size)
    merged.paste(image1, (0, 0))
    merged.paste(image2, offset)

    buffer = BytesIO()
    merged.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def normalize_image(image: PathOrBytes, crop_bbox: bool = True) -> BytesIO:
    base = Image.open(image)
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    premult = base.convert("RGBa")
    if crop_bbox:
        base = base.crop(premult.getbbox())

    buffer = BytesIO()
    base.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def apply_filter(image: PathOrBytes, normalize: bool = True, filter_type: FilterType = FilterType.DEFAULT,
                 scale=1) -> BytesIO:
    if normalize:
        image = normalize_image(image, crop_bbox=False)

    base = Image.open(image)
    if scale != 1:
        base = base.resize(tuple(int(scale * x) for x in base.size), resample=Image.Resampling.NEAREST)

    if filter_type is FilterType.SILHOUETTE:
        return _filter_silhouette(base)
    elif filter_type is FilterType.GAUSSIAN_BLUR:
        return _filter_gaussian_blur(base)
    else:  # FilterType.PIXELATE
        return _filter_pixelate(base)


def _filter_silhouette(image: Image.Image) -> BytesIO:
    w, h = image.size
    mask = Image.new("1", (w, h), 0)
    silhouette = Image.composite(mask, image, image)

    buffer = BytesIO()
    silhouette.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_gaussian_blur(image: Image.Image) -> BytesIO:
    blurred = image.filter(ImageFilter.GaussianBlur(radius=6))

    buffer = BytesIO()
    blurred.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_pixelate(image: Image.Image) -> BytesIO:
    downscaled = image.resize(tuple(int(x / 14) for x in image.size), resample=Image.Resampling.NEAREST)
    upscaled = downscaled.resize(tuple(int(x * 14) for x in downscaled.size), resample=Image.Resampling.NEAREST)

    buffer = BytesIO()
    upscaled.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def save_to_file(path: str, image: BinaryIO) -> None:
    with open(path, "wb") as f:
        f.write(image.read())


if __name__ == "__main__":
    im = Image.open(r"/pokefusion/assets\fusions\custom\57\57.150.png")
