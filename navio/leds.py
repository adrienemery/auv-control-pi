ON = 0
OFF = 1


class Pin:

    def __init__(self, folder_name):
        self.pin = folder_name
        try:
            open("/sys/class/leds/%s/brightness" % self.pin, "w")
        except OSError:
            print("Can't open file 'brightness'")

    def write(self, value):
        with open("/sys/class/leds/%s/brightness" % self.pin, "w") as value_file:
            value_file.write(str(value))


class Led:

    BLACK = (OFF, OFF, OFF)
    RED = (ON, OFF, OFF)
    BLUE = (OFF, ON, OFF)
    GREEN = (OFF, OFF, ON)
    CYAN = (OFF, ON, ON),
    MAGENTA = (ON, OFF, ON)
    YELLOW = (ON, ON, OFF)
    WHITE = (ON, ON, ON)

    def __init__(self):
        self.led_red = Pin("rgb_led0")
        self.led_blue = Pin("rgb_led1")
        self.led_green = Pin("rgb_led2")
        self._color = self.BLACK

        self.led_red.write(OFF)
        self.led_blue.write(OFF)
        self.led_green.write(OFF)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        self.led_red.write(color[0])
        self.led_blue.write(color[1])
        self.led_green.write(color[2])
