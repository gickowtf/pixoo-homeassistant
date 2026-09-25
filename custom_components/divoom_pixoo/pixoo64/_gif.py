"""Helpers for animated images inside ``components`` pages.

A components page is composited into full-screen 64x64 buffers and pushed with
``Draw/SendHttpGif``. When an ``image`` component source holds several frames
(animated GIF/WebP/PNG), the whole page is rendered once per frame and pushed
as one multi-frame animation via :meth:`Pixoo.push_animation`. Static page
content is baked into every frame, so it stays still while the animated part
moves. A single-frame image keeps the exact historical code path.
"""

import logging

from PIL import Image

_LOGGER = logging.getLogger(__name__)

# One frame costs 64*64*3 = 12288 raw bytes (~16 kB base64). Cap the frame
# count so a single page draw cannot flood the device (cf. upstream #153,
# device becoming unresponsive under page rotation). 32 covers the 30-frame
# weather GIF set (~0.5 MB per push, once per page duration).
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
    Frames past ``MAX_ANIMATION_FRAMES`` are dropped with a warning.
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
    for index in range(min(frame_count, MAX_ANIMATION_FRAMES)):
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

    if frame_count > MAX_ANIMATION_FRAMES:
        _LOGGER.warning("Truncating animated image from %s to %s frames.",
                        frame_count, MAX_ANIMATION_FRAMES)

    if not frames:
        return [apply_sizing(img)], clamp_pic_speed(speed_override)

    if speed_override is not None:
        pic_speed = clamp_pic_speed(speed_override)
    elif delays:
        pic_speed = clamp_pic_speed(sum(delays) / len(delays))
    else:
        pic_speed = DEFAULT_PIC_SPEED_MS
    return frames, pic_speed
