# Created by james lewis (baldengineer) 2020-01
# MIT License
# MP730026 Decode Byte Array
# Module to decode the byte stream from a MP730026 DMM
#
# Modified by Albert Degenaar
#
# Heads-up, This code contains bugs
#
# TODO
# Overload on resistance is probably scaled wrong
# hard to capture values

import ustruct
from mp730026_value_table import values, mode_strings, unit_strings
from micropython import const

try:
    import logging
except ImportError:
    NoLogging = True


HOLD = const(0x0100)
REL = const(0x0400)

# region Packet


class packet:
    global NoLogging

    # region Constructor
    def __init__(self, data, debug=False):
        """Constructor

        Arguments:
            data {bytearray} -- the BLE payload from the DMM

        Keyword Arguments:
            debug {bool} -- Do we want to write a bunch of debugging info (default: {False})
        """
        if NoLogging:
            debug = False

        if debug:
            print("Packet Data Type: {}".format(type(data)))
            print("native->{}".format([hex(i) for i in data]))
            print("unpacked->{}".format([hex(i)
                                         for i in ustruct.unpack(">HHBB", data)]))

        self._data = data

        self._debug = debug
        self._hold = (self._data[1] & HOLD) > 0
        self._rel = (self._data[1] & REL) == 0
        self._decimal_position = 5

        mode = self._data[0]  # (self._data[0] << 8) + self._data[1]

        try:
            self._mode_str = mode_strings[str(values[mode][0])]
            self._units_str = unit_strings[str(values[mode][1])]
            self._decimal_position = values[mode][2]

        except KeyError:
            # New mode
            self._mode_str = str(hex(mode))  # its a new mode, so display it
            self._units_str = "?"
            self._decimal_position = 5
            if debug:
                logging.warning("Unexpected mode found: {}".format(hex(mode)))

        self._value = self.decode_reading_into_hex()

    # endregion

    # region __STR__
    def __str__(self):
        return self.DMM_to_string()

    # endregion

    # region Properties
    @property
    def hold(self):
        return self._hold

    @hold.setter
    def hold(self, value):
        self._hold = value

    @property
    def rel(self):
        return self._rel

    @rel.setter
    def rel(self, value):
        self._rel = value

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value

    @property
    def mode(self):
        return self._mode_str

    @mode.setter
    def mode(self, value):
        self._mode_str = value

    @property
    def units(self):
        return self._units_str

    @units.setter
    def units(self, value):
        self._units_str = value

    @property
    def decimal_position(self):
        return self._decimal_position

    @decimal_position.setter
    def decimal_position(self, value):
        self._decimal_position = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    # endregion

    # region Private Helpers
    def decode_reading_into_hex(self):
        """Decode the value for the data packet into Hex

        Arguments:

        Returns:
            string -- Return the value for the data packet
        """
        # get the reading nibbles and create a word
        sign = ""
        if self._data[3] & 0x80 > 0:
            sign = "-"

        readingMSB = self._data[3]
        readingLSB = self._data[2]
        # shift MSB over and add the LSB, creates a 16-bit word
        value = (readingMSB << 8) | readingLSB

        if self.debug:
            logging.info(
                "readingMSB= {}, readingLSB = {}, value={}".format(
                    hex(readingMSB),
                    hex(readingLSB),
                    value
                )
            )

        # strip off the sign bit
        value = value & 0x7FFF

        # convert the integer to a string
        final_value = "{:04d}".format(value)

        if value != 0x7FFF and self.decimal_position < 5:
            # only process decimal if valid, 5 isn't a valid position
            final_value = (
                sign
                + final_value[: self.decimal_position]
                + "."
                + final_value[self.decimal_position:]
            )
        else:
            # there is not a valid display
            final_value = "O.L"  # TODO The decimal shouldn't be hard coded

        return final_value

    def DMM_to_string(self):
        """Translate the data packet from the multimeter into a string

        Arguments:
            data {Array of bytes} -- Data packet from the multimeter

        Returns:
            string -- human readable string
        """
        string_to_print = (
            "Reading [" + self.mode + "]: " + self.value + " " + self.units
        )

        # is hold on?
        if self.hold == True:
            string_to_print += ", HOLD"
        if self.rel == True:
            string_to_print += ", REL"

        if self.debug:
            logging.info(string_to_print)

        return string_to_print


# endregion

# endregion
