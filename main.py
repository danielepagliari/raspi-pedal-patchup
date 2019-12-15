import os
import sys
import time
import RPi.GPIO as GPIO
from rtmidi import API_MACOSX_CORE, API_UNIX_JACK, API_LINUX_ALSA, MidiIn, MidiOut
from rtmidi.midiutil import open_midiinput, open_midioutput
from rtmidi.midiconstants import (BANK_SELECT_LSB, BANK_SELECT_MSB, CHANNEL_PRESSURE,
                                  CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF, PROGRAM_CHANGE)

API = API_LINUX_ALSA
PEDAL_PRESS_CC = 114
PROGRAMS_PER_BANK = 100
N_BANKS = 4
KEYBOARD_STRING = "Nord"
LED_GPIO_PIN = 16

class MidiInputHandler(object):
    def __init__(self, port, midiout, channel = 0):
        self.port = port
        self._midiout = midiout
        self._channel = channel
        self._wallclock = time.time()
        self._debug = False
        self._prog_number = 0
        self._bank_lsb = 0

    def __call__(self, event, data=None):
        message, deltatime = event
        if self._debug:
            self._wallclock += deltatime
            print("[%s] @%0.6f %r" % (self.port, self._wallclock, message))
        if self.is_prog_change(message):
            self.set_prog_number(message)
        if self.is_bank_lsb_change(message):
            self.set_bank_lsb(message)
        if self.is_pedal_release(message):
            self.increment_program()
            self.send_prog_number()

    def is_prog_change(self, message):
        return (message[0] & 0xF0 == PROGRAM_CHANGE
                and message[0] & 0x0F == self._channel)

    # note: bank MSB is fixed at 0 in the NS2ex
    def is_bank_lsb_change(self, message):
        return (message[0] & 0xF0 == CONTROLLER_CHANGE
                and message[0] & 0x0F == self._channel
                and message[1] == BANK_SELECT_LSB)

    def is_pedal_release(self, message):
        return (message[0] & 0xF0 == CONTROLLER_CHANGE
                and message[0] & 0x0F == self._channel
                and message[1] == PEDAL_PRESS_CC
                and message[2] == 0x00)

    def set_prog_number(self, message):
        self._prog_number = message[1]

    def set_bank_lsb(self, message):
        self._bank_lsb = message[2]

    def increment_program(self):
        if self._prog_number < PROGRAMS_PER_BANK - 1:
            self._prog_number += 1
        elif self._bank_lsb < N_BANKS - 1:
            self._prog_number = 0
            self._bank_lsb += 1

    def send_prog_number(self):
        msg = [CONTROLLER_CHANGE + self._channel, BANK_SELECT_LSB, self._bank_lsb]
        midiout.send_message(msg)
        msg = [PROGRAM_CHANGE + self._channel, self._prog_number]
        midiout.send_message(msg)

################################################################################
# Main Progam Start
################################################################################

os.system('echo gpio | tee /sys/class/leds/led0/trigger')

GPIO.setwarnings(False)

# Needs to be BCM. GPIO.BOARD lets you address GPIO ports by periperal
# connector pin number, and the LED GPIO isn't on the connector
GPIO.setmode(GPIO.BCM)

# set up GPIO output channel
GPIO.setup(LED_GPIO_PIN, GPIO.OUT)

try:
    inport = None
    ports = MidiIn(API).get_ports()
    for p in ports:
        if KEYBOARD_STRING in p:
            inport = p
    assert(inport is not None)
    print("Found Midi Input:", inport)
except Exception as exc:
    print("Error probing Midi Input:", exc)
    sys.exit()
except KeyError:
    print("No Midi Input found")
    sys.exit()

try:
    outport = None
    ports = MidiOut(API).get_ports()
    for p in ports:
        if KEYBOARD_STRING in p:
            outport = p
    assert(outport is not None)
    print("Found Midi Output:", outport)
except Exception as exc:
    print("Error probing Midi Output:", exc)
    sys.exit()
except KeyError:
    print("No Midi Output found")
    sys.exit()


try:
    midiin, _ = open_midiinput(inport)
except (EOFError, KeyboardInterrupt):
    print("Error: cannot open Midi Input")
    sys.exit()

try:
    midiout, _ = open_midioutput(outport)
except (EOFError, KeyboardInterrupt):
    print("Error: cannot open Midi Output")
    sys.exit()

print("Attaching MIDI Input callback handler.")
midiin.set_callback(MidiInputHandler(inport, midiout))

print("Entering main loop. Press Control-C to exit.")
try:
    # Just wait for keyboard interrupt,
    # everything else is handled via the input callback.
    while True:
        GPIO.output(LED_GPIO_PIN, GPIO.LOW)
        time.sleep(1)
        GPIO.output(LED_GPIO_PIN, GPIO.HIGH)
        time.sleep(1)
except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    midiin.close_port()
    del midiin
