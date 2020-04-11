import time
import board
import digitalio
from adafruit_debouncer import Debouncer
import adafruit_dotstar
from analogio import AnalogIn
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange

analog_in = AnalogIn(board.A0)  # Set up analog input for pressure sensor
pin = digitalio.DigitalInOut(board.D2)  # Set up digital pin for button
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP
button = Debouncer(pin)  # Use Adafruit Debouncer to track button status
pixels = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)  # Set up built in DotStar
pixels.brightness = 0.2  # Set built in pixel to 20% brightness
white = (255, 255, 255)
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
pixels[0] = blue  # Initial color
midi_channel = 1
midi_breath_ctrl = 2
midi_expr_ctrl = 11
midi_min = 0
midi_max = 127
prev_value = 128

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1],
                          out_channel=midi_channel-1)

class State:
    _holdtime = 1
    _learndelay = .1

    def __init__(self):
        self.mode = 0
        self.readings = []
        self.checkin = time.monotonic()
        self.learntime = time.monotonic()
        self.input_min = 0
        self.input_max = 60500  #input is up to 65535 but voltage is lower

    def update(self):
        if button.rose:  # Called once when button released
            if time.monotonic() - self.checkin > self._holdtime:
                # button was held do calibration
                self.input_max = max(self.readings)
            else:
                # button was pressed change mode
                self.mode = (self.mode + 1) % 3
            if (self.mode == 0):  # Expression CC controller mode
                pixels[0] = green
            elif (self.mode == 1):  # Breath CC controller mode
                pixels[0] = blue
            elif (self.mode == 2):  # Controller off mode
                pixels[0] = red
        elif button.fell:  # Called once when button pushed
            self.checkin = time.monotonic()
            self.learntime = time.monotonic()
            self.readings = []

        if (not button.value):  # Button is pushed
            pixels[0] = white
            if time.monotonic() - self.learntime > self._holdtime:
                self.readings.append(analog_in.value)
                self.learntime = time.monotonic()
            # button is currently pressed collect samples

    def __repr__(self):
        return "<Mode: {}, LastTime: {}>".format(self.mode, self.checkin)

def calibrate_input():
    count = 0
    readings = []
    while count < 20:
        readings.append(analog_in.value)
        count = count + 1
    return max(readings)

def map_to_midi(input_val):
    if (input_val < 0):
        return 0
    result = round((input_val-state.input_min)/(state.input_max-state.input_min)*(midi_max-midi_min)+midi_min)
    if (result < 0):
        result = 0
    if (result > 127):
        result = 127
    return result

state = State()

while True:
    button.update()
    state.update()
    if (state.mode == 0):  # Expession CC controller mode
        intensity = map_to_midi(analog_in.value)
        if (intensity != prev_value):
            midi.send(ControlChange(midi_expr_ctrl, intensity))
            prev_value = intensity
    elif (state.mode == 1):  # Breath CC controller mode
        intensity = map_to_midi(analog_in.value)
        if (intensity != prev_value):
            midi.send(ControlChange(midi_breath_ctrl, intensity))
            prev_value = intensity
