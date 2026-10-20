"""Helpers for animated images inside ``components`` pages.

A components page is composited into full-screen buffers and encoded as one
looping GIF, which the panel plays itself via ``Device/PlayTFGif``, so the
display never shows the HttpGif buffering screen. The bytes stay in memory and
are served to the device through a short-lived signed URL (see ``sensor.py``);
nothing is written under ``www/``. When an ``image`` component source holds
several frames (animated GIF/WebP/PNG), the whole page is rendered once per
frame with static content baked into every frame, so it stays still while the
animated part moves.

That GIF is an **opaque delta**: a full-canvas first frame, later frames
cropped to what changed, ``disposal=1`` and **no transparency flag anywhere** -
disposal 2 is visible on the panel as a blink, and a pixel that carries a
transparency flag is drawn as a white speck.
"""

import hashlib
import logging
from io import BytesIO

from PIL import Image, ImageChops

_LOGGER = logging.getLogger(__name__)

# One frame costs 64*64*3 = 12288 raw bytes (~16 kB base64). Cap the frame
# count so a single page draw cannot flood the device (cf. upstream #153,
# device becoming unresponsive under page rotation). 32 covers a 30-frame
# animation (~0.5 MB per push, once per page duration).
MAX_ANIMATION_FRAMES = 32

# Device takes a single PicSpeed (ms per frame) for the whole animation.
MIN_PIC_SPEED_MS = 50
MAX_PIC_SPEED_MS = 2000
DEFAULT_PIC_SPEED_MS = 200


def clamp_pic_speed(value):
    """Clamp a PicSpeed value into the device-usable range."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PIC_SPEED_MS
    return max(MIN_PIC_SPEED_MS, min(MAX_PIC_SPEED_MS, value))


def _coerce_size(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def extract_frames(img, width=None, height=None, resample_mode=Image.BOX,
                   speed_override=None):
    """Split an opened PIL image into composable frames.

    Returns ``(frames, pic_speed_ms)`` where ``frames`` holds at least one
    ``Image`` (a single-frame source yields ``[img]`` with the component
    sizing applied, exactly like the historical static path) and
    ``pic_speed_ms`` is the device frame delay: ``speed_override`` when set,
    else the mean of the per-frame GIF delays, else the default. All values
    are clamped to ``MIN/MAX_PIC_SPEED_MS``.

    ``width``/``height`` mirror the image component sizing: both set resize
    every frame, one set scales proportionally, neither keeps native size.

    Every frame comes back. The frame cap belongs to the pixel *push*, where
    each frame costs a ~16 kB device post (``MAX_ANIMATION_FRAMES``); a hosted
    page is a URL the panel fetches, so truncating one here would only break
    the art's loop.
    """
    width = _coerce_size(width)
    height = _coerce_size(height)

    def apply_sizing(frame):
        if width and height:
            return frame.resize((width, height), resample_mode)
        sized = frame.copy()
        if width or height:
            sized.thumbnail((100 if not width else width,
                             100 if not height else height),
                            resample_mode)
        return sized

    try:
        frame_count = getattr(img, "n_frames", 1) or 1
    except Exception:  # corrupt source reporting no usable frames
        frame_count = 1

    if frame_count <= 1:
        return [apply_sizing(img)], clamp_pic_speed(speed_override)

    frames = []
    delays = []
    for index in range(frame_count):
        try:
            img.seek(index)
        except EOFError:
            break
        frame = img.copy()  # triggers load, publishing this frame's duration (WebP)
        try:
            delay = int(img.info.get("duration", 0) or 0)
        except (TypeError, ValueError):
            delay = 0
        if delay > 0:
            delays.append(delay)
        frames.append(apply_sizing(frame))

    if not frames:
        return [apply_sizing(img)], clamp_pic_speed(speed_override)

    if speed_override is not None:
        pic_speed = clamp_pic_speed(speed_override)
    elif delays:
        pic_speed = clamp_pic_speed(sum(delays) / len(delays))
    else:
        pic_speed = DEFAULT_PIC_SPEED_MS
    return frames, pic_speed


def _palette_bytes(flat):
    """Serialise a flat ``[r, g, b, ...]`` palette into GIF's 768-byte table.

    Entries past 256 are dropped and a short palette is padded with black, so
    the result is always the 768 bytes the GIF header promises. Both callers
    hold the flat form already - a page's own table is built flat, and
    ``Image.getpalette()`` returns it that way - so flat is the one palette
    contract in this module.
    """
    return bytes(flat[:768]).ljust(768, b"\x00")


def _page_palette(images):
    """One global colour table for every frame of a page.

    Returns ``(palette_frames, palette_bytes, exact)``. A page whose frames
    together hold at most 256 colours gets a table built from exactly those
    colours, so the encode is lossless and the round trip is pixel-exact. A
    richer page is quantised against one shared palette derived from a montage
    of every tenth frame, the trade Pillow's own writer makes.
    """
    colors = set()
    for image in images:
        colors.update(image.getdata())
    if len(colors) <= 256:
        ordered = sorted(colors)
        index = {color: position for position, color in enumerate(ordered)}
        table = [value for rgb in ordered for value in rgb]
        table += [0] * (768 - len(table))
        frames = []
        for image in images:
            frame = Image.new("P", image.size)
            frame.putpalette(table)
            frame.putdata([index[color] for color in image.getdata()])
            frames.append(frame)
        return frames, _palette_bytes(table), True

    step = max(1, len(images) // 10)
    picked = list(range(0, len(images), step))
    montage = Image.new("RGB", (images[0].width, images[0].height * len(picked)))
    for position, index in enumerate(picked):
        montage.paste(images[index], (0, images[0].height * position))
    base = montage.quantize(colors=256)
    frames = [image.quantize(palette=base, dither=Image.NONE) for image in images]
    return frames, _palette_bytes(base.getpalette() or []), False


def _image_block(frame):
    """Return one P-mode frame's GIF image block (image descriptor + LZW data).

    GIF has no delta-frame primitive Pillow exposes, and Pillow's own optimize
    pass can only crop a frame by tagging the unchanged pixels transparent -
    which is exactly what the panel draws as white specks. So each frame is
    written by Pillow as a one-image GIF (the LZW stream is the part we want)
    and the image block is cut out of that file; the
    caller rewrites the descriptor's position and size and writes its own
    Graphic Control Extension. ``optimize=False`` is what keeps Pillow from
    renumbering the palette: the indices in this block must be the indices of
    the page's one global colour table.
    """
    buffer = BytesIO()
    frame.save(buffer, format="GIF", optimize=False, interlace=False)
    blob = buffer.getvalue()
    if blob[:6] not in (b"GIF87a", b"GIF89a"):
        raise ValueError("Pillow did not write a GIF")
    position = 13 + 3 * 2 ** ((blob[10] & 0x07) + 1)
    while position < len(blob):
        block = blob[position]
        if block == 0x21:  # extension: skip its sub-block chain
            cursor = position + 2
            while blob[cursor] != 0:
                cursor += 1 + blob[cursor]
            position = cursor + 1
        elif block == 0x2C:  # image descriptor
            if blob[position + 9] & 0x80:
                raise ValueError(
                    "Pillow wrote a local colour table; the page encoder "
                    "promises one global palette")
            cursor = position + 11  # descriptor + LZW minimum code size
            while blob[cursor] != 0:
                cursor += 1 + blob[cursor]
            return blob[position:cursor + 1]
        else:
            raise ValueError(f"unexpected GIF block 0x{block:02x}")
    raise ValueError("Pillow's GIF held no image block")


def _graphic_control_extension(delay_cs, disposal=1):
    """GCE carrying a delay, no user input and **no transparency**.

    The transparency bit and the transparent-colour-index byte are both zero on
    purpose: a frame that carries a transparency flag is what the panel renders
    with white specks, so no frame of a hosted page may have one.
    """
    packed = (disposal & 0x07) << 2
    return bytes((0x21, 0xF9, 0x04, packed,
                  delay_cs & 0xFF, (delay_cs >> 8) & 0xFF, 0x00, 0x00))


def _screen_descriptor(size):
    """Logical screen descriptor: global colour table, 256 entries, bg 0."""
    return bytes((size & 0xFF, (size >> 8) & 0xFF,
                  size & 0xFF, (size >> 8) & 0xFF,
                  0xF7, 0x00, 0x00))


def _patch_descriptor(block, rect):
    """Point a spliced image block at ``rect`` (left, top, width, height)."""
    left, top, width, height = rect
    patched = bytearray(block)
    patched[1:3] = left.to_bytes(2, "little")
    patched[3:5] = top.to_bytes(2, "little")
    patched[5:7] = width.to_bytes(2, "little")
    patched[7:9] = height.to_bytes(2, "little")
    return bytes(patched)


def encode_page_gif(frames, size, pic_speed_ms):
    """Encode composited RGB buffers as one looping GIF for hosted playback.

    ``frames`` are raw RGB buffers (``size*size*3`` ints) as returned by
    :meth:`Pixoo.get_buffer`. Every frame must be a full-canvas opaque image.

    The published shape is an **opaque delta**: frame 0 full canvas, later
    frames cropped to what changed, ``disposal=1`` everywhere, no transparent
    index anywhere and one global colour table. Disposal 2 is
    restore-to-background, so the decoder clears each frame's rectangle before
    painting the next one and the panel shows that clear as a blink. A
    full-canvas frame is not needed to make the delta composite correctly
    either - only *transparency* breaks it (the panel draws a pixel it was told
    to skip as a white speck), which is why the frames are assembled here
    instead of saved by Pillow: see :func:`_image_block`.

    Every frame carries the same delay and the file loops forever.

    Returns ``(blob, digest)``: the GIF bytes to hand to the device, and an
    8-char content hash over the **input** frames and the picture speed, so
    the hosted player's skip gate does not depend on the encoding.
    """
    expected = size * size * 3
    if not frames:
        raise ValueError("encode_page_gif needs at least one frame")
    for frame in frames:
        if len(frame) != expected:
            raise ValueError(
                f"frame holds {len(frame)} values, expected {expected}")
    pic_speed_ms = clamp_pic_speed(pic_speed_ms)
    images = [Image.frombytes("RGB", (size, size), bytes(frame))
              for frame in frames]
    digest = hashlib.md5(
        b"".join(bytes(frame) for frame in frames)
        + str(pic_speed_ms).encode()).hexdigest()[:8]
    palette_frames, palette, exact = _page_palette(images)
    if not exact:
        _LOGGER.debug("Page holds more than 256 colours; quantising to one palette.")
    delay_cs = max(1, int(round(pic_speed_ms / 10.0)))

    planned = []
    previous = images[0]
    for index, image in enumerate(images):
        if index == 0:
            box = (0, 0, size, size)
        else:
            box = ImageChops.difference(image, previous).getbbox()
            previous = image
            if box is None:
                # identical to the frame before it: carry its duration on the
                # previous frame rather than writing the picture twice
                # (Pillow's writer merges these the same way)
                if planned:
                    planned[-1][3] += delay_cs
                continue
        # ``getbbox`` gives (left, top, right, bottom); the image descriptor
        # wants (left, top, width, height).
        rect = (box[0], box[1], box[2] - box[0], box[3] - box[1])
        planned.append([box, rect, palette_frames[index], delay_cs])

    blob = bytearray(b"GIF89a")
    blob += _screen_descriptor(size)
    blob += palette
    # NETSCAPE2.0 application extension, loop count 0 = forever, right after the
    # global colour table where a decoder expects it.
    blob += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    for box, rect, frame, delay in planned:
        blob += _graphic_control_extension(delay)
        blob += _patch_descriptor(_image_block(frame.crop(box)), rect)
    blob += b"\x3b"

    return bytes(blob), digest
