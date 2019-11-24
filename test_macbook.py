import sys
import time
from rtmidi import API_MACOSX_CORE, API_UNIX_JACK, API_LINUX_ALSA, MidiIn, MidiOut
from rtmidi.midiutil import open_midiinput, open_midioutput
from rtmidi.midiconstants import (BANK_SELECT_LSB, BANK_SELECT_MSB, CHANNEL_PRESSURE,
                                  CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF, PROGRAM_CHANGE)

API = API_MACOSX_CORE
PEDAL_PRESS_CC = 114
PROGRAMS_PER_BANK = 100
N_BANKS = 4

class MidiInputHandler(object):
    def __init__(self, port, midiout, channel = 0):
        self.port = port
        self._midiout = midiout
        self._channel = channel
        self._wallclock = time.time()
        self._debug = True
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
        if self.is_pedal_press(message):
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

    def is_pedal_press(self, message):
        return (message[0] & 0xF0 == CONTROLLER_CHANGE
                and message[0] & 0x0F == self._channel
                and message[1] == PEDAL_PRESS_CC)

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


try:
    inport = MidiIn(API).get_ports()[0]
    print("Found Midi Input:", inport)
except Exception as exc:
    print("Error probing Midi Input:", exc)
    sys.exit()
except KeyError:
    print("No Midi Input found")
    sys.exit()

try:
    outport = MidiOut(API).get_ports()[0]
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
        time.sleep(1)
except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    midiin.close_port()
    del midiin
