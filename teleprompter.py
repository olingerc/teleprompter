from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

import threading
from evdev import InputDevice, list_devices, categorize


FOOT_SWITCH_DEVICE_NAME_SUFFIX = "FootSwitch Keyboard"


class InputMonitor(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.label = Label(text="Waiting for footswitch input...", font_size="24sp")
        self.add_widget(self.label)
        self.input_state = None

        # Check for Foot Switch
        self.fs_device = self.find_foot_switch_device()

        # If keyboard we need this:
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up,)
        self.previous_state_a = None
        self.previous_state_b = None
        self.previous_state_c = None

        # Start the input listener thread
        threading.Thread(target=self.detect_events, daemon=True).start()

        # Schedule UI update
        Clock.schedule_interval(self.update_label, 0.5)

    def find_foot_switch_device(self):
        fs_device = None
        devices = [InputDevice(path) for path in list_devices()]

        for device in devices:
            if device.name.endswith(FOOT_SWITCH_DEVICE_NAME_SUFFIX):
                print(f"Found {FOOT_SWITCH_DEVICE_NAME_SUFFIX} at {device.path}")
                fs_device = device
                break
        if fs_device is None:
            print(
                f"Did not find {FOOT_SWITCH_DEVICE_NAME_SUFFIX}"
            )
            print("Will try working with keyboard")
            if len(devices)> 0:
                print("Found:")
                for device in devices:
                    print(device)
        return fs_device

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

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None


    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        btn = None
        state = None
        if key == "1" or key =="numapd1":
            btn = "KEY_A"
            if self.previous_state_a == "press":
                state = "hold"
            else:
                state = "down"
        if key == "2" or key =="numapd2":
            btn = "KEY_B"
            if self.previous_state_b == "press":
                state = "hold"
            else:
                state = "down"
        if key == "3" or key =="numapd3":
            btn = "KEY_C"
            if self.previous_state_c == "press":
                state = "hold"
            else:
                state = "down"
        if key == "escape":
            # Stop listener
            keyboard.release()

        if btn and state:
            self.input_state = (btn, state)
        return True

    def _on_keyboard_up(self, keyboard, keycode):
        key = keycode[1]
        btn = None
        state = None
        if key == "1" or key =="numapd1":
            btn = "KEY_A"
            state = "up"
        if key == "2" or key =="numapd2":
            btn = "KEY_B"
            state = "up"
        if key == "3" or key =="numapd3":
            btn = "KEY_C"
            state = "up"
        if btn and state:
            self.input_state = (btn, state)
        if key == "escape":
            # Stop listener
            keyboard.release()
        return True

    def update_label(self, dt):
        if self.input_state:
            self.label.text = f"Last input: {self.input_state}"
        else:
            self.label.text = "Waiting for input..."


class TelePrompterApp(App):
    def build(self):
        return InputMonitor()


if __name__ == "__main__":
    try:
        TelePrompterApp().run()
    except Exception as e:
        raise e
