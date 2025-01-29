import random
import time
import math

import board
import displayio
import framebufferio
import rgbmatrix

class Buffer:
    def __init__(self, bitmap, group):
        self.bitmap = bitmap
        self.group = group

    @property
    def width(self):
        return self.bitmap.width

    @property
    def height(self):
        return self.bitmap.height

    def fill(self, value):
        self.bitmap.fill(value)

    def __getitem__(self, index):
        return self.bitmap[index]

    def __setitem__(self, index, value):
        self.bitmap[index] = value

class Screensaver:
    def __init__(self, display):
        self.reset()

    def reset(self):
        self.display = display
        self.palette = self._get_palette()
        self._buffer1 = self._setup_buffer(root=True)
        self._buffer2 = self._setup_buffer()
        self._useSecondaryBuffer = False
        self._reset_buffer(self._buffer1)
        self._reset_buffer(self._buffer2)
    
    @property
    def width(self):
        return self.display.width

    @property
    def height(self):
        return self.display.height
    
    def _setup_buffer(self, root=False):
        bitmap = displayio.Bitmap(self.width, self.height, len(self.palette))
    
        grid = displayio.TileGrid(bitmap, pixel_shader=self.palette)
        group = displayio.Group()
        group.append(grid)
    
        if root:
            self.display.root_group = group
    
        return Buffer(bitmap, group)

    def _get_palette(self):
        pass
    
    def _reset_buffer(self, buffer):
        pass
    
    def draw(self, prev_buffer, current_buffer):
        pass

    def run(self):
        display.refresh()
        
        if self._useSecondaryBuffer:
            self.display.root_group = self._buffer1.group
            self.draw(self._buffer1, self._buffer2)
        else:
            display.root_group = self._buffer2.group
            self.draw(self._buffer2, self._buffer1)
        
        self._useSecondaryBuffer = not self._useSecondaryBuffer

class MatrixScreensaver(Screensaver):
    def __init__(self, display):
        super().__init__(display)
        self.recent_rows = [] 

    def _get_palette(self):
        num_colors = 16
        palette = displayio.Palette(num_colors)
    
        color_step = 255 / (num_colors - 1);
    
        for i in range(num_colors):
            green_value = math.floor(i * color_step)
            palette[i] = (0, green_value, 0)

        return palette

    def _reset_buffer(self, buffer):
        buffer.fill(0)
    
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

class PipesScreenSaver(Screensaver):
    def __init__(self, display):
        super().__init__(display)
        self.num_pipes = 0
        self.new_pipe()

    def _get_palette(self):
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

        palette = displayio.Palette(len(colors))
        for i, color in enumerate(colors):
            palette[i] = color

        return palette
    
    def _reset_buffer(self, buffer):
        buffer.fill(0)

    def new_pipe(self):
        self.ticks_without_turn = 0
        self.num_pipes += 1
        
        self.color = random.randint(1, len(self.palette) - 1)
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

screensaver_type = -1;
def new_screensaver(display):
    global screensaver_type
    
    while True:
        new_screensaver = random.randint(0, 1)
        if new_screensaver != screensaver_type:
            screensaver_type = new_screensaver
            break

    screensaver = None
    if screensaver_type == 0:
        screensaver = MatrixScreensaver(display)
    elif screensaver_type == 1:
        screensaver = PipesScreenSaver(display)
    
    return screensaver

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
screensaver = new_screensaver(display)

while True:
    for _ in range(500):
        screensaver.run()
    
    screensaver = new_screensaver(display)

