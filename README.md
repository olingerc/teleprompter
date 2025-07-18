# Teleprompter Appp

## Requirements

`pip install kivy evdev python-pptx pdf2image`


## Prepare system:

input reading needs sudo access or
`sudo usermod -aG input $USER`

## For WSL2
- `sudo apt install libmtdev-dev libreoffice poppler-utils`


## Inestigating my Foot Switch

`sudo evtest`

```
Bus 001 Device 004: ID 3553:b001 PCsensor FootSwitch

/dev/input/event7:      PCsensor FootSwitch Keyboard
/dev/input/event8:      PCsensor FootSwitch Mouse
/dev/input/event9:      PCsensor FootSwitch
```

### Finding events of My footswitch

Using evdev I found:

device.path device.name device.phys

```
/dev/input/event9 PCsensor FootSwitch usb-0000:01:00.0-1.2/input1
/dev/input/event8 PCsensor FootSwitch Mouse usb-0000:01:00.0-1.2/input0
/dev/input/event7 PCsensor FootSwitch Keyboard usb-0000:01:00.0-1.2/input0
```

```
/dev/input/event7
dev = InputDevice("/dev/input/event7")
for event in dev.read_loop():
    if event.type == ecodes.KEY_A:
        print(categorize(event))

key event at 1752780066.426953, 30 (KEY_A), down
akey event at 1752780066.705412, 30 (KEY_A), hold   (repeats if holding)
key event at 1752780066.741179, 30 (KEY_A), up

bkey event at 1752780072.955876, 48 (KEY_B), up
key event at 1752780078.412572, 46 (KEY_C), down
```

## From Powerpoint to prompt

- https://github.com/jdhao/pptx_to_image