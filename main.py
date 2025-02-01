from abc import ABCMeta, abstractmethod
import random
import time
import math

import board
import displayio
import framebufferio
import rgbmatrix

class Buffer:
    def __init__(self, bitmap, palette):
        self._group = displayio.Group()
        self._bitmap = bitmap
        self.swap_palette(palette)

    @property
    def width(self):
        return self.bitmap.width

    @property
    def height(self):
        return self.bitmap.height

    @property
    def group(self):
        return self._group

    def fill(self, value):
        self._bitmap.fill(value)

    def __getitem__(self, index):
        return self._bitmap[index]

    def __setitem__(self, index, value):
        self._bitmap[index] = value

    def swap_palette(self, palette):
        grid = displayio.TileGrid(self._bitmap, pixel_shader=palette)
        if len(self._group) > 0:
            self._group.pop()
        
        self._group.append(grid)

class Screensaver(metaclass=ABCMeta):
    def __init__(self):
        self._viewport_width = 0
        self._viewport_height = 0
    
    @property
    def width(self):
        return self._viewport_width

    @property
    def height(self):
        return self._viewport_height

    def is_viewport_valid(self):
        return self.width > 0 and self.height > 0

    def reset_viewport(self, width, height):
        self._viewport_width = width
        self._viewport_height = height
        self.reset()

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def get_palette(self):
        return displayio.Palette(0)

    def reset_buffer(self, buffer):
        buffer.fill(0)

    @abstractmethod
    def draw(self, prev_buffer, current_buffer):
        pass

class MatrixScreensaver(Screensaver):
    def reset(self):
        self.recent_rows = []
        
    def get_palette(self):
        num_colors = 16
        palette = displayio.Palette(num_colors)
    
        color_step = 255 / (num_colors - 1);
    
        for i in range(num_colors):
            green_value = math.floor(i * color_step)
            palette[i] = (0, green_value, 0)

        return palette
    
    def draw(self, prev_buffer, current_buffer):
        current_buffer.fill(0)
        
        for y in range(self.height):
            for x in reversed(range(self.width - 1)):
                value = prev_buffer[(x, y)]
    
                current_buffer[(x + 1, y)] = value
    
                if value == 15:
                    current_buffer[(x, y)] = value - 3
                    continue
    
                if random.random() < 0.3:
                    value -= 1
                
                current_buffer[(x, y)] = max(value, 0)
    
        y = 0
        while True:
            y = random.randint(0, self.height - 1)
            if not y in self.recent_rows:
                break
            
        self.recent_rows.append(y)
        if len(self.recent_rows) > 10:
            self.recent_rows.pop()
        
        if random.random() < 0.4:
            current_buffer[(0, y)] = 15

class PipesScreensaver(Screensaver):
    colors = [
        0x000000,
        0xe0e0e0,
        0xcc6666,
        0xde935f,
        0xf0c674,
        0xb5bd68,
        0x8abeb7,
        0x81a2be,
        0xb294bb,
    ]
    
    def reset(self):
        self.num_pipes = 0
        self.new_pipe()

    def get_palette(self):
        palette = displayio.Palette(len(self.colors))
        for i, color in enumerate(self.colors):
            palette[i] = color

        return palette

    def new_pipe(self):
        self.ticks_without_turn = 0
        self.num_pipes += 1
        
        self.color = random.randint(1, len(self.colors) - 1)
        self.direction = random.randint(0, 3)

        if self.direction == 0:
            self.position = (0, random.randint(1, self.height - 2))
        elif self.direction == 1:
            self.position = (random.randint(1, self.width - 2), self.height - 1)
        elif self.direction == 2:
            self.position = (self.width - 1, random.randint(1, self.height - 2))
        elif self.direction == 3:
            self.position = (random.randint(1, self.width - 2), 0)
        
    def draw(self, prev_buffer, current_buffer):
        if self.num_pipes > 10:
            self._reset_buffer(current_buffer)
            self.num_pipes = 0
        else:
            for y in range(self.height):
                for x in range(self.width):
                    current_buffer[(x, y)] = prev_buffer[(x, y)]
        
        current_buffer[self.position] = self.color
        
        x, y = self.position
        if self.direction == 0:
            self.position = (x + 1, y)
        elif self.direction == 1:
            self.position = (x, y - 1)
        elif self.direction == 2:
            self.position = (x - 1, y)
        elif self.direction == 3:
            self.position = (x, y + 1)

        turn_chance = (self.ticks_without_turn - 1) / 25
        if random.random() < turn_chance:
            turning = 1
            if random.random() < 0.5:
                turning = -1

            self.direction = (self.direction + turning) % 4
            self.ticks_without_turn = 0
        else:
            self.ticks_without_turn += 1
        
        x, y = self.position
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            self.new_pipe()

class ScreensaverManager:
    def __init__(self, display):
        self.screensavers = []
        self._current_screensaver = -1
        self._display = display

        self._buffer1 = self._setup_buffer()
        self._buffer2 = self._setup_buffer()
        self._use_secondary_buffer = False

        self.reset()

    @property
    def current_screensaver(self):
        if 0 <= self._current_screensaver < len(self.screensavers):
            return self.screensavers[self._current_screensaver]

        return None

    def _setup_buffer(self):
        bitmap = displayio.Bitmap(self._display.width, self._display.height, 16)
    
        return Buffer(bitmap, displayio.Palette(0))

    def reset(self):
        if self.current_screensaver == None:
            return
        
        screensaver = self.current_screensaver
        
        screensaver.reset_viewport(
            width=self._display.width,
            height=self._display.height,
        )

        palette = screensaver.get_palette()
        self._buffer1.swap_palette(palette)
        self._buffer2.swap_palette(palette)

        screensaver.reset_buffer(self._buffer1)
        screensaver.reset_buffer(self._buffer2)

        self._display.root_group = self._buffer1.group
        self._use_secondary_buffer = False
        self._display.refresh()

    def add(self, screensaver):
        self.screensavers.append(screensaver)

        # First item
        if len(self.screensavers) == 1:
            self.cycle()
    
    def cycle(self):
        num_screensavers = len(self.screensavers)
        
        if num_screensavers == 0:
            return
        elif num_screensavers == 1:
            self._current_screensaver = 0
            return
        
        while True:
            new_screensaver = random.randint(0, num_screensavers - 1)
            if new_screensaver != self._current_screensaver:
                self._current_screensaver = new_screensaver
                break

        self.reset()

    def run(self):
        if self.current_screensaver == None:
            return
        elif not self.current_screensaver.is_viewport_valid():
            self.reset()
            return

        print(self._buffer1[0])
        self._display.refresh()
        if self._use_secondary_buffer:
            self._display.root_group = self._buffer1.group
            self.current_screensaver.draw(self._buffer1, self._buffer2)
        else:
            display._root_group = self._buffer2.group
            self.current_screensaver.draw(self._buffer2, self._buffer1)
        
        self._use_secondary_buffer = not self._use_secondary_buffer

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

screensavers = ScreensaverManager(display)
screensavers.add(MatrixScreensaver())
screensavers.add(PipesScreensaver())
screensavers.cycle()

while True:
    for _ in range(500):
        screensavers.run()
    
    screensavers.cycle()
