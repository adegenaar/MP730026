from ssd1306_setup import WIDTH, HEIGHT, setup
from writer import Writer, CWriter

# Fonts
import Fonts.freesans20 as freesans20
import Fonts.font6 as small


class display:
    def __init__(self, use_spi=False, soft=False):
        self.ssd = setup(use_spi, soft)
        self.freesans = Writer(self.ssd, freesans20, verbose=False)
        self.arial = Writer(self.ssd, small, verbose=False)
        #            x, y,  w, h
        self.auto = [WIDTH-40, 0, WIDTH, 11]
        self.hold = [0, 0, 40, 11]
        self.mode = [0, 11, WIDTH - 1, 30]
        self.value = [0, 41, WIDTH-1, HEIGHT-1]

    def Hold(self, on):
        Writer.set_textpos(self.ssd, self.hold[1], self.hold[0])
        if on:
            self.arial.printstring('HOLD', 1)
        else:
            self.ssd.fill_rect(
                self.hold[0], self.hold[1], self.hold[2], self.hold[3], 0)
            self.arial.printstring('    ', 0)

    def Auto(self, auto, mode):
        Writer.set_textpos(self.ssd, self.auto[1], self.auto[0])
        self.ssd.fill_rect(self.auto[0], self.auto[1],
                           self.auto[2], self.auto[3], 0)
        if mode == 'Temperature' or mode == 'Non-Contact':
            self.arial.printstring("    ", 0)
        elif (auto):
            self.arial.printstring("REL ", 0)
        else:
            self.arial.printstring("AUTO", 1)

    def Mode(self, mode):
        Writer.set_textpos(self.ssd, self.mode[1], self.mode[0])
        self.ssd.fill_rect(self.mode[0], self.mode[1],
                           self.mode[2], self.mode[3], 0)
        self.freesans.printstring(mode)

    def Value(self, value):
        Writer.set_textpos(self.ssd, self.value[1], self.value[0])
        self.ssd.fill_rect(
            self.value[0], self.value[1], self.value[2], self.value[3], 0)
        self.freesans.printstring(value)

    def Update(self, hold, rel, mode, value):
        self.Hold(hold)
        self.Mode(mode)
        self.Value(value)
        self.Auto(rel, mode)
        self.ssd.show()

    def Clear(self):
        self.ssd.fill_rect(0, 0, WIDTH-1, HEIGHT-1, 0)
        self.ssd.show()
