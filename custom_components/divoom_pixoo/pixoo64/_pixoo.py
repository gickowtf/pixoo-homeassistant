import base64
import json
from datetime import timedelta
from enum import IntEnum

import requests
from PIL import Image, ImageOps

from ._colors import get_rgb
from ._font import retrieve_glyph, retrieve_glyph_width, FONT_GICKO, FONT_PICO_8, FIVE_PIX, ELEVEN_PIX, CLOCK

import logging
_LOGGER = logging.getLogger(__name__)

def clamp(value, minimum=0, maximum=255):
    if value > maximum:
        return maximum
    if value < minimum:
        return minimum

    return value


def clamp_color(rgb):
    return clamp(rgb[0]), clamp(rgb[1]), clamp(rgb[2])


def lerp(start, end, interpolant):
    return start + interpolant * (end - start)


def lerp_location(xy1, xy2, interpolant):
    return lerp(xy1[0], xy2[0], interpolant), lerp(xy1[1], xy2[1], interpolant)


def minimum_amount_of_steps(xy1, xy2):
    return max(abs(xy1[0] - xy2[0]), abs(xy1[1] - xy2[1]))


def rgb_to_hex_color(rgb):
    return f'#{rgb[0]:0>2X}{rgb[1]:0>2X}{rgb[2]:0>2X}'


def round_location(xy):
    return round(xy[0]), round(xy[1])


class Channel(IntEnum):
    FACES = 0
    CLOUD = 1
    VISUALIZER = 2
    CUSTOM = 3


class ImageResampleMode(IntEnum):
    PIXEL_ART = Image.NEAREST


class TextScrollDirection(IntEnum):
    LEFT = 0
    RIGHT = 1


class Pixoo:
    __buffer = []
    __buffers_send = 0
    __counter = 0
    __refresh_counter_limit = 32
    timeout = 9

    def __init__(self, address, size=64, debug=False, refresh_connection_automatically=True):
        assert size in [16, 32, 64], \
            'Invalid screen size in pixels given. ' \
            'Valid options are 16, 32, and 64'

        self.refresh_connection_automatically = refresh_connection_automatically
        self.address = address
        self.debug = debug
        self.size = size

        # Total number of pixels
        self.pixel_count = self.size * self.size

        # Generate URL
        self.__url = 'http://{0}/post'.format(address)

        # Prefill the buffer
        self.fill()

        # Retrieve the counter
        self.__load_counter()

        # Resetting if needed
        if self.refresh_connection_automatically and self.__counter > self.__refresh_counter_limit:
            self.__reset_counter()


    def clear(self, rgb: object = get_rgb("black")) -> object:
        self.fill(rgb)

    def clear_rgb(self, r, g, b):
        self.fill_rgb(r, g, b)


    def draw_character_at_location_rgb(self, character, x=0, y=0, r=255, g=255,
                                       b=255):
        self.draw_character(character, (x, y), (r, g, b))

    def draw_filled_rectangle(self, top_left_xy=(0, 0), bottom_right_xy=(1, 1),
                              rgb=get_rgb("black")):
        for y in range(top_left_xy[1], bottom_right_xy[1] + 1):
            for x in range(top_left_xy[0], bottom_right_xy[0] + 1):
                self.draw_pixel((x, y), rgb)

    def draw_filled_rectangle_from_top_left_to_bottom_right_rgb(self,
                                                                top_left_x=0,
                                                                top_left_y=0,
                                                                bottom_right_x=1,
                                                                bottom_right_y=1,
                                                                r=0, g=0, b=0):
        self.draw_filled_rectangle((top_left_x, top_left_y),
                                   (bottom_right_x, bottom_right_y), (r, g, b))

    def draw_image(self, image_path_or_object, xy=(0, 0),
                   image_resample_mode=ImageResampleMode.PIXEL_ART,
                   pad_resample=False):
        image = image_path_or_object if isinstance(image_path_or_object,
                                                   Image.Image) else Image.open(
            image_path_or_object)
        size = image.size
        width = size[0]
        height = size[1]

        # See if it needs to be scaled/resized to fit the display
        if width > self.size or height > self.size:
            if pad_resample:
                image = ImageOps.pad(image, (self.size, self.size),
                                     image_resample_mode)
            else:
                image.thumbnail((self.size, self.size), image_resample_mode)

            if self.debug:
                print(
                    f'[.] Resized image to fit on screen (saving aspect ratio): "{image_path_or_object}" ({width}, {height}) '
                    f'-> ({image.size[0]}, {image.size[1]})')

        # Convert the loaded image to RGBA
        rgba_image = image.convert('RGBA')

        # Iterate over all pixels in the image that are left and buffer them
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                location = (x, y)
                placed_x = x + xy[0]
                if self.size - 1 < placed_x or placed_x < 0:
                    continue

                placed_y = y + xy[1]
                if self.size - 1 < placed_y or placed_y < 0:
                    continue

                if rgba_image.getpixel(location)[3] != 0:  # If the pixel is transparent, it won't be drawn.
                    self.draw_pixel((placed_x, placed_y),
                                    rgba_image.getpixel(location))

    def draw_image_at_location(self, image_path_or_object, x, y,
                               image_resample_mode=ImageResampleMode.PIXEL_ART):
        self.draw_image(image_path_or_object, (x, y), image_resample_mode)

    def draw_line(self, start_xy, stop_xy, rgb=get_rgb("white")):
        line = set()

        # Calculate the amount of steps needed between the points to draw a nice line
        amount_of_steps = minimum_amount_of_steps(start_xy, stop_xy)

        # Iterate over them and create a nice set of pixels
        for step in range(amount_of_steps):
            if amount_of_steps == 0:
                interpolant = 0
            else:
                interpolant = step / amount_of_steps

            # Add a pixel as a rounded location
            line.add(
                round_location(lerp_location(start_xy, stop_xy, interpolant)))

        # Draw the actual pixel line
        for pixel in line:
            self.draw_pixel(pixel, rgb)

    def draw_line_from_start_to_stop_rgb(self, start_x, start_y, stop_x, stop_y,
                                         r=255, g=255, b=255):
        self.draw_line((start_x, start_y), (stop_x, stop_y), (r, g, b))

    def draw_pixel(self, xy, rgb):
        # If it's not on the screen, we're not going to bother
        if xy[0] < 0 or xy[0] >= self.size or xy[1] < 0 or xy[1] >= self.size:
            if self.debug:
                limit = self.size - 1
                print(
                    f'[!] Invalid coordinates given: ({xy[0]}, {xy[1]}) (maximum coordinates are ({limit}, {limit})')
            return

        # Calculate the index
        index = xy[0] + (xy[1] * self.size)

        # Color it
        self.draw_pixel_at_index(index, rgb)

    def draw_pixel_at_index(self, index, rgb):
        # Validate the index
        if index < 0 or index >= self.pixel_count:
            if self.debug:
                print(f'[!] Invalid index given: {index} (maximum index is {self.pixel_count - 1})')
            return

        # Clamp the color, just to be safe
        rgb = clamp_color(rgb)

        # Move to place in array
        index = index * 3

        self.__buffer[index] = rgb[0]
        self.__buffer[index + 1] = rgb[1]
        self.__buffer[index + 2] = rgb[2]

    def draw_pixel_at_index_rgb(self, index, r, g, b):
        self.draw_pixel_at_index(index, (r, g, b))

    def draw_pixel_at_location_rgb(self, x, y, r, g, b):
        self.draw_pixel((x, y), (r, g, b))

    def draw_character(self, character, xy=(0, 0), rgb=get_rgb("white"), font=None):
        if font is None:
            font = FONT_PICO_8
        matrix = retrieve_glyph(character, font)
        if matrix is not None:
            x_size = matrix[-1]
            for index, bit in enumerate(matrix):
                if bit == 1 and index != len(matrix) - 1:
                    local_x = index % x_size
                    local_y = int(index / x_size)
                    self.draw_pixel((xy[0] + local_x, xy[1] + local_y), rgb)

    def draw_text(self, text, xy=(0, 0), rgb=get_rgb("white"), font=None, align="left"):
        if font is None:
            font = FONT_PICO_8

        y_offset = 0
        for line in text.split("\n"):
            if align == "center":
                x_offset = int(self.get_text_width(line, font) / 2) * -1
            elif align == "right":
                x_offset = self.get_text_width(line, font) * -1
            else:
                x_offset = 0
            
            for index, character in enumerate(line):
                if retrieve_glyph(character, font) is None:
                    _LOGGER.error("Unknown character '" + str(character) + "'.")
                    character = "?"

                self.draw_character(character, (x_offset + xy[0], y_offset + xy[1]), rgb, font)
                x_offset += retrieve_glyph(character, font)[-1] + 1
            
            # Since for now every character is at least smaller than the '0', this works.
            dummy_char = retrieve_glyph("0", font)
            height = int( (len(dummy_char)-1) / dummy_char[-1] )
            y_offset += height+1
    
    def get_text_width(self, text, font=None):
        if font is None:
            font = FONT_PICO_8

        length = 0
        for index, character in enumerate(text):
            length += retrieve_glyph_width(character, font) + 1

        return length - 1

    def draw_text_at_location_rgb(self, text, x, y, r, g, b):
        self.draw_text(text, (x, y), (r, g, b))

    def fill(self, rgb=get_rgb("black")):
        self.__buffer = []
        rgb = clamp_color(rgb)
        for index in range(self.pixel_count):
            self.__buffer.extend(rgb)

    def fill_rgb(self, r, g, b):
        self.fill((r, g, b))

    def push(self):
        self.__send_buffer()

    def send_text(self, text, xy=(0, 0), color=get_rgb("white"), identifier=1,
                  font=2, width=64,
                  movement_speed=0,
                  direction=TextScrollDirection.LEFT):


        # Make sure the identifier is valid
        identifier = clamp(identifier, 0, 19)

        response = requests.post(self.__url, json.dumps({
            'Command': 'Draw/SendHttpText',
            'TextId': identifier,
            'x': xy[0],
            'y': xy[1],
            'dir': direction,
            'font': font,
            'TextWidth': width,
            'speed': movement_speed,
            'TextString': text,
            'color': rgb_to_hex_color(color)
        }), timeout=self.timeout)

        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def set_brightness(self, brightness):
        # This won't be possible
        brightness = clamp(brightness, 0, 100)
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/SetBrightness',
            'Brightness': brightness
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def set_channel(self, channel):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/SetIndex',
            'SelectIndex': int(channel)
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def set_clock(self, clock_id):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/SetClockSelectId',
            'ClockId': int(clock_id)
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def set_custom_channel(self, index):
        self.set_custom_page(index)
        self.set_channel(3)

    def set_custom_page(self, index):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/SetCustomPageIndex',
            'CustomPageIndex': index
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def play_gif(self, gif_url):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Device/PlayTFGif',
            'FileType': 2,
            'FileName': gif_url
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def set_face(self, face_id):
        self.set_clock(face_id)

    def set_screen(self, on=True):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/OnOffScreen',
            'OnOff': 1 if on else 0
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def restart_device(self):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Device/SysReboot'
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def get_state(self):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/GetAllConf'
        }), timeout=self.timeout)
        data = response.json()
        _LOGGER.debug("Device Data (" + str(self.address) + "): " + str(data))
        return data['LightSwitch'] == 1

    def get_brightness(self):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/GetAllConf'
        }), timeout=self.timeout)
        data = response.json()
        return data['Brightness']

    def set_screen_off(self):
        self.set_screen(False)

    def set_screen_on(self):
        self.set_screen(True)

    def set_visualizer(self, equalizer_position):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Channel/SetEqPosition',
            'EqPosition': equalizer_position
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    # buzz_time 	Working time of buzzer in one cycle in milliseconds
    # idle_time		Idle time of buzzer in one cycle in milliseconds
    # total_time	Working total time of buzzer in milliseconds
    # This is according to the Divoom Docs.
    def play_buzzer(self, buzz_cycle_time: timedelta, idle_cycle_time: timedelta, total_time: timedelta):
        response = requests.post(self.__url, json.dumps({
            'Command': 'Device/PlayBuzzer',
            'ActiveTimeInCycle': buzz_cycle_time.total_seconds() * 1000,
            'OffTimeInCycle': idle_cycle_time.total_seconds() * 1000,
            'PlayTotalTime': total_time.total_seconds()*1000
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)

    def __clamp_location(self, xy):
        return clamp(xy[0], 0, self.size - 1), clamp(xy[1], 0, self.size - 1)

    def __error(self, error):
        if self.debug:
            print('[x] Error on request ' + str(self.__counter))
            print(error)

    def __load_counter(self):
        response = requests.post(self.__url, '{"Command": "Draw/GetHttpGifId"}', timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)
        else:
            self.__counter = int(data['PicId'])
            if self.debug:
                print('[.] Counter loaded and stored: ' + str(self.__counter))

    def __send_buffer(self):

        # Add to the internal counter
        self.__counter = self.__counter + 1

        # Check if we've passed the limit and reset the counter for the animation remotely
        if self.refresh_connection_automatically and self.__counter >= self.__refresh_counter_limit:
            self.__reset_counter()
            self.__counter = 1

        if self.debug:
            print(f'[.] Counter set to {self.__counter}')
            # Simulate this too I suppose
            self.__buffers_send = self.__buffers_send + 1
            return

        # Encode the buffer to base64 encoding
        response = requests.post(self.__url, json.dumps({
            'Command': 'Draw/SendHttpGif',
            'PicNum': 1,
            'PicWidth': self.size,
            'PicOffset': 0,
            'PicID': self.__counter,
            'PicSpeed': 1000,
            'PicData': str(base64.b64encode(bytearray(self.__buffer)).decode())
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)
        else:
            self.__buffers_send = self.__buffers_send + 1

            if self.debug:
                print(f'[.] Pushed {self.__buffers_send} buffers')

    def __reset_counter(self):
        if self.debug:
            print(f'[.] Resetting counter remotely')
        response = requests.post(self.__url, json.dumps({
            'Command': 'Draw/ResetHttpGifId'
        }), timeout=self.timeout)
        data = response.json()
        if data['error_code'] != 0:
            self.__error(data)


__all__ = (Channel, ImageResampleMode, Pixoo, TextScrollDirection)
