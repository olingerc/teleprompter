import os
import subprocess

from pdf2image import convert_from_bytes

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.properties import ObjectProperty
from kivy.uix.image import Image

from pptx import Presentation

import threading
from evdev import InputDevice, list_devices, categorize


FOOT_SWITCH_DEVICE_NAME_SUFFIX = "FootSwitch Keyboard"
BLACK = [0, 0, 0, 1]
WHITE = [1, 1, 1, 1]

HOME_MIN_ROWS_NUM = 3
HOME_MIN_COLS_NUM = 6


class SongCard(
    BoxLayout,
):

    focus = ObjectProperty()  # Expose to template

    def __init__(
        self,
        sequence=None,
        artist=None,
        song=None,
        index=None,
        is_placeholder=False,
        images=None,
        number_of_slides=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        opacity = 1
        if is_placeholder:
            opacity = 0
        BoxLayout.__init__(self, padding="100sp", opacity=opacity)

        self.index = index

        if is_placeholder is False:

            self.orientation = "vertical"
            self.focus = False
            self.images = images
            self.number_of_slides = number_of_slides

            self.sequence_label_widget = Label(
                text=sequence, font_size="18sp", color=WHITE
            )
            self.artist_label_widget = Label(text=artist, font_size="24sp", color=WHITE)
            self.song_label_widget = Label(
                text=song,
                font_size="24sp",
                color=WHITE,
                width=self.width,
            )
            self.song_label_widget.text_size = (self.song_label_widget.width, None)
            self.add_widget(self.sequence_label_widget)
            self.add_widget(self.artist_label_widget)
            self.add_widget(self.song_label_widget)

    def set_focus(self, focus=True):
        self.focus = focus


class Prompt(BoxLayout):

    def __init__(self, images = None, number_of_slides=None, **kwargs):
        super().__init__(**kwargs)
        self.images = images
        self.drawn_images = []
        self.current_image_number = 0
        self.number_of_slides = number_of_slides

    def draw_first_image(self):
        for p in self.drawn_images:
            self.remove_widget(p)

        image = Image(source=self.images[0])
        self.drawn_images.append(image)
        self.add_widget(image)
    
    def next_image(self):
        if self.current_image_number + 1 > self.number_of_slides - 1:
            return
        else:
            for p in self.drawn_images:
                self.remove_widget(p)
            image = Image(source=self.images[self.current_image_number + 1])
            self.drawn_images.append(image)
            self.add_widget(image)
            
            self.current_image_number = self.current_image_number + 1
    
    def prev_image(self):
        if self.current_image_number -1 < 0:
            return
        else:
            for p in self.drawn_images:
                self.remove_widget(p)
            image = Image(source=self.images[self.current_image_number - 1])
            self.drawn_images.append(image)
            self.add_widget(image)
            
            self.current_image_number = self.current_image_number - 1
        


class TeleprompterMain(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.input_state = None

        # Check for Foot Switch
        self._fs_device = self._find_foot_switch_device()
        threading.Thread(target=self._detect_foot_switch_events, daemon=True).start()

        # If keyboard we need this
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(
            on_key_down=self._on_keyboard_down,
            on_key_up=self._on_keyboard_up,
        )
        self._previous_keyboard_state = None

        # Build our UI
        self.mode = "home"  # home or prompt
        self.focused_card = None
        self.card_instances = None
        self.cards = self._load_songbook()
        self.placeholders_num = 0
        self._initialize_ui()

    def _load_songbook(self):
        songbook_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "songbook"
        )
        cards = []
        if os.path.exists(songbook_folder):
            for f in os.listdir(songbook_folder):
                if f.endswith("pptx"):
                    info = f.replace(".pptx", "")
                    number_of_slides = self._number_of_slides(os.path.join(songbook_folder, f))
                    card = {
                        "sequence": info.split("-")[0].strip(),
                        "artist": info.split("-")[1].strip(),
                        "song": info.split("-")[2].strip(),
                        "images": self._presentation_to_images(
                            os.path.join(songbook_folder, f),
                            number_of_slides,
                        ),
                        "number_of_slides": number_of_slides
                    }
                    cards.append(card)
        if len(cards) == 0:
            return [
                {"sequence": "1", "artist": "A", "song": "Hallo"},
                {"sequence": "2", "artist": "B", "song": "Me"},
                {"sequence": "3", "artist": "C", "song": "Too"},
                {"sequence": "4", "artist": "D", "song": "Sing"},
            ]
        else:
            return cards

    def _find_foot_switch_device(self):
        fs_device = None
        devices = [InputDevice(path) for path in list_devices()]

        for device in devices:
            if device.name.endswith(FOOT_SWITCH_DEVICE_NAME_SUFFIX):
                print(f"Found {FOOT_SWITCH_DEVICE_NAME_SUFFIX} at {device.path}")
                fs_device = device
                break
        if fs_device is None:
            print(f"Did not find {FOOT_SWITCH_DEVICE_NAME_SUFFIX}")
            print("Will try working with keyboard")
            if len(devices) > 0:
                print("Found:")
                for device in devices:
                    print(device)
        return fs_device

    def _detect_foot_switch_events(self):
        if self._fs_device:
            with self._fs_device.grab_context():
                for ev in self._fs_device.async_read_loop():
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
        # Do not unbind, otherwise escape from prompt will switch to home but then no keys are detected anymore
        pass
        #self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        #self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        btn = None
        state = None
        if key == "1" or key == "numapd1":
            btn = "KEY_A"
            if self._previous_keyboard_state == "down" + btn:
                state = "hold"
            else:
                state = "down"
        if key == "2" or key == "numapd2":
            btn = "KEY_B"
            if self._previous_keyboard_state == "down" + btn:
                state = "hold"
            else:
                state = "down"
        if key == "3" or key == "numapd3":
            btn = "KEY_C"
            if self._previous_keyboard_state == "down" + btn:
                state = "hold"
            else:
                state = "down"
        if key == "escape":
            # Stop listener
            if self.mode == "home":
                keyboard.release()
                App.get_running_app().stop()
            else:
                self.set_mode("home")
                self._keyboard.bind(
                    on_key_down=self._on_keyboard_down,
                    on_key_up=self._on_keyboard_up,
                )

        if btn and state:
            self.input_state = (btn, state)
            self._previous_keyboard_state = state + btn
            self._decide_action()
        return True

    def _on_keyboard_up(self, keyboard, keycode):
        key = keycode[1]
        btn = None
        state = None
        if key == "1" or key == "numapd1":
            btn = "KEY_A"
            state = "up"
        if key == "2" or key == "numapd2":
            btn = "KEY_B"
            state = "up"
        if key == "3" or key == "numapd3":
            btn = "KEY_C"
            state = "up"
        if btn and state:
            self.input_state = (btn, state)
            # self._decide_action()
        if key == "escape":
            # Stop listener
            keyboard.release()
        return True

    def _decide_action(self):
        if self.input_state:
            if self.mode == "home":
                if self.input_state[0] == "KEY_A" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_previous_card()
                if self.input_state[0] == "KEY_C" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_next_card()

                if self.input_state[0] == "KEY_B" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.enter_prompt()
            else:
                if self.input_state[0] == "KEY_A" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.prompt_widget.prev_image()
                if self.input_state[0] == "KEY_C" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.prompt_widget.next_image()

                if self.input_state[0] == "KEY_B" and self.input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.set_mode("home")

    def _initialize_ui(self):

        # Window level
        # Window.fullscreen = True
        Window.allow_screensaver = False

        # Main box (Create Grid for Home and Box for Prompt)
        self.home_layout = GridLayout(
            cols=HOME_MIN_COLS_NUM,
            rows=HOME_MIN_ROWS_NUM,
            spacing=10,
            padding=10,
            orientation="lr-tb",
        )
        self.prompt_layout = BoxLayout(opacity=0)
        self.add_widget(self.home_layout)
        self.add_widget(self.prompt_layout)

        # Fill home
        # Do we need placeholders
        if len(self.cards) < HOME_MIN_COLS_NUM * HOME_MIN_ROWS_NUM:
            to_add = HOME_MIN_COLS_NUM * HOME_MIN_ROWS_NUM - len(self.cards)
            self.placeholders_num = to_add
            while to_add > 0:
                self.cards.append(
                    {
                        "is_placeholder": True,
                        "sequence": None,
                        "artist": None,
                        "song": None,
                    }
                )
                to_add = to_add - 1

        # Create card widgets and place into grid
        self.card_instances = []
        for index, c in enumerate(self.cards):
            c_instance = SongCard(
                sequence=c["sequence"],
                artist=c["artist"],
                song=c["song"],
                images=c.get("images", []),
                is_placeholder=c.get("is_placeholder", False),
                number_of_slides=c.get("number_of_slides"),
                index=index,
            )
            self.home_layout.add_widget(c_instance)
            self.card_instances.append(c_instance)
        self.card_instances[0].set_focus()
        self.focused_card = self.card_instances[0]

        # Fill Prompt
        self.prompt_widget = Prompt()
        self.prompt_layout.add_widget(self.prompt_widget)

    def _number_of_slides(self, path_to_presentation):
        prs = Presentation(path_to_presentation)
        return len(prs.slides)

    def _presentation_to_images(self, ppt_path, num_slides):
        IMAGE_FORMAT = "jpg"
        OUT_DIR = "ppt-previews"
        if not os.path.exists(OUT_DIR):
            os.mkdir(OUT_DIR)

        ###start = time.time()
        print("Start converting your PPT to {} images.".format(IMAGE_FORMAT))

        filename_bare = os.path.basename(ppt_path).replace(".pptx", "")
        
        # Give cache if images are present
        expected_image_paths = []
        cache_ok = True
        for i in range(num_slides):
            expected_image = os.path.join(OUT_DIR, f"{filename_bare}-{i}.{IMAGE_FORMAT}")
            expected_image_paths.append(expected_image)
            if os.path.exists(expected_image) is False:
                cache_ok = False
        if cache_ok:
            print("Taking cached image")
            return expected_image_paths

        # convert pptx to PDF
        command_list = ["soffice", "--headless", "--convert-to", "pdf", ppt_path]
        subprocess.run(command_list)

        pdffile_name = filename_bare + ".pdf"
        with open(pdffile_name, "rb") as f:
            pdf_bytes = f.read()
        images = convert_from_bytes(pdf_bytes, dpi=96 * 4)

        created_image_paths = []
        for i, img in enumerate(images):
            im_name = os.path.join(OUT_DIR, f"{filename_bare}-{i}.{IMAGE_FORMAT}")
            created_image_paths.append(im_name)
            img.save(im_name)
        os.unlink(pdffile_name)
        
        return created_image_paths

    def focus_previous_card(self):
        next_index = self.focused_card.index - 1
        if next_index < 0:
            next_index = len(self.card_instances) - 1 - self.placeholders_num
        for c in self.card_instances:
            if c.index == next_index:
                c.set_focus(True)
                self.focused_card = c
            else:
                c.set_focus(False)

    def focus_next_card(self):
        next_index = self.focused_card.index + 1
        if next_index >= len(self.card_instances) - self.placeholders_num:
            next_index = 0
        for c in self.card_instances:
            if c.index == next_index:
                c.set_focus(True)
                self.focused_card = c
            else:
                c.set_focus(False)

    def enter_prompt(self):
        self.prompt_widget.images = self.focused_card.images
        self.prompt_widget.number_of_slides = self.focused_card.number_of_slides
        self.prompt_widget.draw_first_image()
        self.set_mode("prompt")

    def set_mode(self, mode):
        if mode == "prompt":
            self.mode = "prompt"
            self.home_layout.opacity = 0
            self.prompt_layout.opacity = 1
        else:
            self.mode = "home"
            self.home_layout.opacity = 1
            self.prompt_layout.opacity = 0


class TeleprompterApp(App):
    def build(self):
        main = TeleprompterMain()
        return main


if __name__ == "__main__":
    TeleprompterApp().run()
