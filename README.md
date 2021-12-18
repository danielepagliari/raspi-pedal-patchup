# Raspberry Pi Pedal Patch-Up

A Python script for Raspberry Pi that converts MIDI signals allowing to use the latch/rotor pedal in the Nord Stage 2ex keyboard to do Program Up on press (a functionality not supported by the keyboard OS). Easily customizable for other keyboards as well.


## Install Instructions:

```
sudo apt-get install python3 python3-pip libasound2-dev
sudo pip3 install python-rtmidi # sudo is required here
```

Check this or any other guide for how to let the service run at startup:
```
https://www.dexterindustries.com/howto/run-a-program-on-your-raspberry-pi-at-startup/
```


