from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout

import threading
from evdev import InputDevice, list_devices, categorize
from pynput.keyboard import Key, Listener

FOOT_SWITCH_DEVICE_NAME_SUFFIX = "FootSwitch Keyboard"
WIRED_KEYBOARD_DEVICE_NAME_SUFFIX = "Wired Keyboard"


class InputMonitor(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.label = Label(text="Waiting for footswitch input...", font_size="24sp")
        self.add_widget(self.label)
        self.input_state = None

        # Check for Foot Switch
        self.fs_device, self.kb_device = self.find_input_devices()
        
        # If keyboard we need this:
        self.previous_state_a = None
        self.previous_state_b = None
        self.previous_state_c = None

        # Start the input listener thread
        threading.Thread(target=self.detect_events, daemon=True).start()

        # Schedule UI update
        Clock.schedule_interval(self.update_label, 0.5)

    def find_input_devices(self):
        fs_device = None
        kb_device = None
        devices = [InputDevice(path) for path in list_devices()]

        for device in devices:
            if device.name.endswith(FOOT_SWITCH_DEVICE_NAME_SUFFIX):
                print(f"Found {FOOT_SWITCH_DEVICE_NAME_SUFFIX} at {device.path}")
                fs_device = device
                break
        for device in devices:
            if device.name.endswith(WIRED_KEYBOARD_DEVICE_NAME_SUFFIX):
                print(f"Found {WIRED_KEYBOARD_DEVICE_NAME_SUFFIX} at {device.path}")
                kb_device = device
                break
        if fs_device is None and kb_device is None:
            print(f"Did not find {FOOT_SWITCH_DEVICE_NAME_SUFFIX} or {WIRED_KEYBOARD_DEVICE_NAME_SUFFIX}")
            print("Found")
            for device in devices:
                print(device)
            print("Expect strange behaviour")
        return fs_device, kb_device

    def detect_events(self):
        if self.fs_device:
            with self.fs_device.grab_context():
                for ev in self.fs_device.async_read_loop():
                    btn = None
                    state = None
                    as_string = str(categorize(ev))
                    if "KEY_A" in as_string:
                        btn = "KEY_A"
                    elif "KEY_B" in as_string:
                        btn = "KEY_B"
                    elif "KEY_C" in as_string:
                        btn = "KEY_C"

                    if "up" in as_string:
                        state = "up"
                    elif "down" in as_string:
                        state = "down"
                    elif "hold" in as_string:
                        state = "hold"

                    if btn and state:
                        self.input_state = (btn, state)
        elif self.kb_device:
            with self.kb_device.grab_context():
                for ev in self.kb_device.async_read_loop():
                    btn = None
                    state = None
                    as_string = str(categorize(ev))
                    if "KEY_1" in as_string:
                        btn = "KEY_A"
                    elif "KEY_2" in as_string:
                        btn = "KEY_B"
                    elif "KEY_3" in as_string:
                        btn = "KEY_C"

                    if "up" in as_string:
                        state = "up"
                    elif "down" in as_string:
                        state = "down"
                    elif "hold" in as_string:
                        state = "hold"

                    if btn and state:
                        self.input_state = (btn, state)
        else:
            # Collect events until released
            with Listener(
                    on_press=self.on_press,
                    on_release=self.on_release) as listener:
                listener.join()

    def on_press(self, key):
        btn = None
        state = None
        print(key.value() == "1")
        if str(key) == "1":
            btn = "KEY_A"
            if self.previous_state_a == "press":
                state = "hold"
            else:
                state = "down"
        if key == "2":
            btn = "KEY_B"
            if self.previous_state_b == "press":
                state = "hold"
            else:
                state = "down"
        if key == "3":
            btn = "KEY_C"
            if self.previous_state_c == "press":
                state = "hold"
            else:
                state = "down"
        print(key, btn)

        if btn and state:
            self.input_state = (btn, state)

    def on_release(self, key):
        btn = None
        state = None
        if key == "1":
            btn = "KEY_A"
            state = "up"
        if key == "2":
            btn = "KEY_B"
            state = "up"
        if key == "3":
            btn = "KEY_C"
            state = "up"
        if btn and state:
            self.input_state = (btn, state)
        if key == Key.esc:
            # Stop listener
            return False

    def update_label(self, dt):
        if self.input_state:
            self.label.text = f"Last input: {self.input_state}"
        else:
            self.label.text = "Waiting for input..."


class TelePrompterApp(App):
    def build(self):
        return InputMonitor()


if __name__ == "__main__":
    TelePrompterApp().run()
