from enum import Enum, auto
from io import BytesIO
from typing import IO

import numpy as np
from PIL import Image, ImageFile, ImageFilter
from skimage.transform import swirl

from pokefusion.types import StrPath

type RGB = tuple[int, int, int]
type RGBA = tuple[int, int, int, int]
type ImageIO = StrPath | IO[bytes]

ImageFile.LOAD_TRUNCATED_IMAGES = True


class Orientation(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()


class Alignment(Enum):
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    CENTER = auto()


class FilterType(Enum):
    SILHOUETTE = auto()
    GAUSSIAN_BLUR = auto()
    PIXELATE = auto()
    GRAYSCALE = auto()
    EDGE = auto()
    BOX = auto()
    SWIRL = auto()


def _offset(alignment: Alignment, container: int, item: int) -> int:
    if alignment in (Alignment.BOTTOM, Alignment.RIGHT):
        return container - item
    if alignment is Alignment.CENTER:
        return (container - item) // 2
    return 0


def get_dominant_color(image: ImageIO, normalize: bool = False) -> RGB:
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


def zoom_image(image: ImageIO, factor: int = 2) -> BytesIO:
    base = Image.open(image)
    zoomed = base.resize(tuple(int(factor * x) for x in base.size), resample=Image.Resampling.NEAREST)

    buffer = BytesIO()
    zoomed.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def pad_image(image: ImageIO) -> BytesIO:
    base = Image.open(image)
    old_width, old_height = base.size
    new_width, new_height = old_width + 100, old_height + 100

    padded = Image.new("RGBA", (new_width, new_height))
    padded.paste(base, ((new_width - old_width) // 2, (new_height - old_height) // 2))

    buffer = BytesIO()
    padded.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def merge_images(
        image1: ImageIO,
        image2: ImageIO,
        orientation: Orientation = Orientation.HORIZONTAL,
        pixel_gap: int = 2,
        crop_bbox: bool = True,
        alignment: Alignment = Alignment.BOTTOM,
) -> BytesIO:
    image1 = normalize_image(image1, crop_bbox=crop_bbox)
    image2 = normalize_image(image2, crop_bbox=crop_bbox)

    image1 = Image.open(image1)
    image2 = Image.open(image2)

    if orientation is Orientation.HORIZONTAL:
        size = (image1.width + image2.width + pixel_gap, max(image1.height, image2.height))
        pos1 = (0, _offset(alignment, size[1], image1.height))
        pos2 = (image1.width + pixel_gap, _offset(alignment, size[1], image2.height))
    else:
        size = (max(image1.width, image2.width), image1.height + image2.height + pixel_gap)
        pos1 = (_offset(alignment, size[0], image1.width), 0)
        pos2 = (_offset(alignment, size[0], image2.width), image1.height + pixel_gap)

    merged = Image.new("RGBA", size)
    merged.paste(image1, pos1)
    merged.paste(image2, pos2)

    buffer = BytesIO()
    merged.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def normalize_image(image: ImageIO, crop_bbox: bool = True) -> BytesIO:
    base = Image.open(image)

    if base.mode != "RGBA":
        base = base.convert("RGBA")

    if crop_bbox:
        premult = base.convert("RGBa")
        base = base.crop(premult.getbbox())

    buffer = BytesIO()
    base.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def apply_filter(image: ImageIO, normalize: bool = True, filter_type: FilterType = FilterType.SILHOUETTE,
                 scale: int = 1) -> BytesIO:
    if normalize:
        image = normalize_image(image, crop_bbox=True if filter_type is FilterType.SWIRL else False)

    base = Image.open(image)
    if scale != 1:
        base = base.resize(tuple(int(scale * x) for x in base.size), resample=Image.Resampling.NEAREST)

    if filter_type is FilterType.SILHOUETTE:
        return _filter_silhouette(base)
    elif filter_type is FilterType.GAUSSIAN_BLUR:
        return _filter_gaussian_blur(base)
    elif filter_type is FilterType.PIXELATE:
        return _filter_pixelate(base)
    elif filter_type is FilterType.GRAYSCALE:
        return _filter_grayscale(base)
    elif filter_type is FilterType.EDGE:
        return _filter_edge(base)
    elif filter_type is FilterType.BOX:
        return _filter_box(base)
    elif filter_type is FilterType.SWIRL:
        return _filter_swirl(base)
    else:
        return _filter_noop(base)


def _filter_noop(image: Image.Image) -> BytesIO:
    buffer = BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


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


def _filter_pixelate(image: Image.Image, factor: int = 14) -> BytesIO:
    downscaled = image.resize(tuple(int(x / factor) for x in image.size), resample=Image.Resampling.NEAREST)
    upscaled = downscaled.resize(tuple(int(x * factor) for x in downscaled.size), resample=Image.Resampling.NEAREST)

    buffer = BytesIO()
    upscaled.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_grayscale(image: Image.Image) -> BytesIO:
    grayscaled = image.convert("L")

    buffer = BytesIO()
    grayscaled.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_edge(image: Image.Image) -> BytesIO:
    edge = image.filter(ImageFilter.FIND_EDGES)

    buffer = BytesIO()
    edge.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_box(image: Image.Image) -> BytesIO:
    downscaled = image.resize(tuple(int(x / 14) for x in image.size), resample=Image.Resampling.NEAREST)
    upscaled = downscaled.resize(tuple(int(x * 14) for x in downscaled.size), resample=Image.Resampling.NEAREST)
    box = upscaled.convert("L").filter(ImageFilter.FIND_EDGES)

    buffer = BytesIO()
    box.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


def _filter_swirl(image: Image.Image) -> BytesIO:
    radius = min(image.size)
    a = to_numpy(image)
    swirled = swirl(a, rotation=0, strength=30, radius=radius)

    buffer = BytesIO()
    Image.fromarray((swirled * 255).astype(np.uint8)).save(buffer, "PNG")
    buffer.seek(0)

    return buffer




def to_numpy(im: Image.Image):
    """https://uploadcare.com/blog/fast-import-of-pillow-images-to-numpy-opencv-arrays/"""
    im.load()
    # unpack data
    e = Image._getencoder(im.mode, 'raw', im.mode)
    e.setimage(im.im, (0, 0) + im.size)

    # NumPy buffer for the result
    shape, typestr = Image._conv_type_shape(im)
    data = np.empty(shape, dtype=np.dtype(typestr))
    mem = data.data.cast('B', (data.data.nbytes,))

    bufsize, s, offset = 65536, 0, 0
    while not s:
        l, s, d = e.encode(bufsize)
        mem[offset:offset + len(d)] = d
        offset += len(d)
    if s < 0:
        raise RuntimeError("encoder error %d in tobytes" % s)
    return data
