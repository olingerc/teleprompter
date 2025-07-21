import subprocess
import threading
import os
from timeit import main

from evdev import InputDevice, list_devices, categorize

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty

from pdf2image import convert_from_bytes
from pptx import Presentation


FOOT_SWITCH_DEVICE_NAME_SUFFIX = "FootSwitch Keyboard"
BLACK = [0, 0, 0, 1]
WHITE = [1, 1, 1, 1]

SONGBOOK_MIN_ROWS_NUM = 3
SONGBOOK_MIN_COLS_NUM = 6

SONGBOOKS_FOLDER = "songbooks"
TEMP_FOLDER = "converted"


class Songbook(BoxLayout):
    title = StringProperty()
    sequence = StringProperty()
    cards = ObjectProperty()
    focus = ObjectProperty()
    index = ObjectProperty()

class SequenceLabel(Label):
    pass


class ArtistLabel(Label):
    pass


class SongLabel(Label):
    pass


class SongCard(
    BoxLayout,
):

    focus = ObjectProperty()
    is_placeholder = BooleanProperty()
    sequence = ObjectProperty()
    artist = ObjectProperty()
    song = ObjectProperty()

    def __init__(
        self,
        sequence=None,
        artist=None,
        song=None,
        index=None,
        is_placeholder=False,
        images=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.focus = False

        self.index = index
        self.is_placeholder = is_placeholder
        self.images = images
        self.sequence = str(index + 1)
        self.artist = artist
        self.song = song

    def set_focus(self, focus=True):
        self.focus = focus


class BackButton(
    BoxLayout,
):
    focus = ObjectProperty()



class LoadingScreenLayout(BoxLayout):
    previous_text = ""

    def draw_text(self, text):
        self.ls_text = self.previous_text + "\n" + text
        self.previous_text = self.previous_text + "\n" + text

class HomeLayout(BoxLayout):
    pass

class SongbookLayoutMain(BoxLayout):
    pass

class SongbookLayoutList(GridLayout):
    pass


class PromptLayout(BoxLayout):
    current_image_number = ObjectProperty(0)
    current_image_source = ObjectProperty()
    number_of_slides = ObjectProperty()
    
    current_card = ObjectProperty()
    next_card = ObjectProperty()
    
    all_cards = ObjectProperty()
    placeholders_num = ObjectProperty()

    def load(self, current_card):
        
        # Prepare first draw
        self.current_card = current_card
        self.images = current_card.images
        self.number_of_slides = len(current_card.images)
        self.current_image_number = 0
        self.current_image_source = self.images[0]
        self.next_card = self.get_next_card()
    
    def get_previous_card(self):
        next_index = self.current_card.index - 1
        if next_index < 0:
            next_index = len(self.all_cards) - 1 - self.placeholders_num
        for c in self.all_cards:
            if c.index == next_index:
                return c
        return None

    def get_next_card(self):
        next_index = self.current_card.index + 1
        if next_index >= len(self.all_cards) - self.placeholders_num:
            next_index = 0
        for c in self.all_cards:
            if c.index == next_index:
                return c
        return None
    
    def prev_image(self):
        if self.current_image_number - 1 < 0:
            to_load = self.get_previous_card()
            self.load(to_load)
        else:
            self.current_image_number = self.current_image_number - 1
            self.current_image_source = self.images[self.current_image_number]

    def next_image(self):
        if self.current_image_number + 1 > self.number_of_slides - 1:
            to_load = self.get_next_card()
            self.load(to_load)
        else:
            self.current_image_number = self.current_image_number + 1
            self.current_image_source = self.images[self.current_image_number]


class PrompterTopBar(BoxLayout):
    pass


class PrompterBottomBar(BoxLayout):
    pass


class TeleprompterWidget(FloatLayout):

    mode = StringProperty("loading")  # Expose to template
    current_songbook = ObjectProperty()

    focused_songbook = ObjectProperty()
    focused_card = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._input_state = None
        self._card_instances = None
        self._placeholders_num = 0

        self.song_books = []
        # Check for Foot Switch
        self._fs_device = self._find_foot_switch_device()
        threading.Thread(target=self._detect_foot_switch_events, daemon=True).start()

        # Connect Keyboard
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(
            on_key_down=self._on_keyboard_down,
            on_key_up=self._on_keyboard_up,
        )
        self._previous_keyboard_state = None

    """
    Setup UI
    """

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
                        self._input_state = (btn, state)
                        self._decide_action()

    def _keyboard_closed(self):
        # Do not unbind, otherwise escape from prompt will switch to home but then no keys are detected anymore
        pass
        # self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        # self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        btn = None
        state = None
        if key == "1" or key == "numpad1":
            btn = "KEY_A"
            if self._previous_keyboard_state == "down" + btn:
                state = "hold"
            else:
                state = "down"
        if key == "2" or key == "numpad2":
            btn = "KEY_B"
            if self._previous_keyboard_state == "down" + btn:
                state = "hold"
            else:
                state = "down"
        if key == "3" or key == "numpad3":
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
            elif self.mode == "songbook":
                self.set_mode("home")
                self._keyboard.bind(
                    on_key_down=self._on_keyboard_down,
                    on_key_up=self._on_keyboard_up,
                )
            else:
                self.set_mode("songbook")
                self._keyboard.bind(
                    on_key_down=self._on_keyboard_down,
                    on_key_up=self._on_keyboard_up,
                )

        if btn and state:
            self._input_state = (btn, state)
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
            self._input_state = (btn, state)
            # self._decide_action()
        return True

    def _decide_action(self):
        if self._input_state:
            if self.mode == "home":
                if self._input_state[0] == "KEY_A" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_previous_songbook()
                if self._input_state[0] == "KEY_C" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_next_songbook()

                if self._input_state[0] == "KEY_B" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.songbook_open(self.focused_songbook)
            elif self.mode == "songbook":
                if self._input_state[0] == "KEY_A" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_previous_card()
                if self._input_state[0] == "KEY_C" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.focus_next_card()

                if self._input_state[0] == "KEY_B" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.enter_prompt()
            else:
                if self._input_state[0] == "KEY_A" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.prompt_prev()
                if self._input_state[0] == "KEY_C" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.prompt_next()

                if self._input_state[0] == "KEY_B" and self._input_state[1] in [
                    "hold",
                    "down",
                ]:
                    self.set_mode("songbook")

    """
    Actions
    """

    def focus_previous_card(self):
        
        # Handle back button
        if self.ids["back_button"].focus is True:
            next_index = len(self._card_instances) - 1 - self._placeholders_num
            self.ids["back_button"].focus = False
        else:
            next_index = self.focused_card.index - 1    

        if next_index < 0:
            self.ids["back_button"].focus = True
        for c in self._card_instances:
            if c.index == next_index:
                c.set_focus(True)
                self.focused_card = c
            else:
                c.set_focus(False)

    def focus_next_card(self):

        # Handle back button
        if self.ids["back_button"].focus is True:
            next_index = 0
            self.ids["back_button"].focus = False
        else:
            next_index = self.focused_card.index + 1

        if next_index >= len(self._card_instances) - self._placeholders_num:
            self.ids["back_button"].focus = True
        for c in self._card_instances:
            if c.index == next_index:
                c.set_focus(True)
                self.focused_card = c
            else:
                c.set_focus(False)

    def focus_previous_songbook(self):
        next_index = self.focused_songbook.index - 1
        if next_index < 0:
            next_index = len(self.song_books) - 1
        for sb in self.song_books:
            if sb.index == next_index:
                sb.focus = True
                self.focused_songbook = sb
            else:
                sb.focus = False

    def focus_next_songbook(self):
        next_index = self.focused_songbook.index + 1
        if next_index >= len(self.song_books):
            next_index = 0
        for sb in self.song_books:
            if sb.index == next_index:
                sb.focus = True
                self.focused_songbook = sb
            else:
                sb.focus = False

    def enter_prompt(self):
        if self.ids["back_button"].focus is True:
            self.set_mode("home")
            return
        
        self.ids["prompt_layout"].load(self.focused_card)
        self.set_mode("prompt")

    def prompt_prev(self):
        self.ids["prompt_layout"].prev_image()

    def prompt_next(self):
        self.ids["prompt_layout"].next_image()

    def songbook_open(self, songbook):
        self.ids["back_button"].focus = False
        self.initialize_songbook(songbook)
        self.set_mode("songbook")

    def set_mode(self, mode):
        self.mode = mode

    """
    Load Song Books
    """

    def _number_of_slides(self, path_to_presentation):
        prs = Presentation(path_to_presentation)
        return len(prs.slides)

    def _presentation_to_images(self, ppt_path, num_slides, songbook_name):
        IMAGE_FORMAT = "jpg"
        OUT_DIR = TEMP_FOLDER + "/" + songbook_name
        if not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR)

        ### start = time.time()
        message = "Converting {}.".format(os.path.basename(ppt_path))
        self.ids["ls_screen"].draw_text(message)
        filename_bare = os.path.basename(ppt_path).replace(".pptx", "")

        # Give cache if images are present but only if ppt is not newer
        expected_image_paths = []
        cache_ok = True
        for i in range(num_slides):
            expected_image = os.path.join(
                OUT_DIR, f"{filename_bare}-{i}.{IMAGE_FORMAT}"
            )
            expected_image_paths.append(expected_image)
            if os.path.exists(expected_image) is False:
                cache_ok = False
            else:
                if os.path.getmtime(expected_image) < os.path.getmtime(ppt_path):
                    cache_ok = False
                    self.ids["ls_screen"].draw_text("cache obsolete")
        if cache_ok:
            self.ids["ls_screen"].draw_text("taking from cache")
            return expected_image_paths

        # convert pptx to PDF
        self.ids["ls_screen"].draw_text("converted")
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

    def load_songbooks(self):
        songbooks_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), SONGBOOKS_FOLDER
        )
        if os.path.exists(songbooks_folder) is False:
            raise Exception(f"Songbooks folder {songbooks_folder} does not exist.")
        
        self.song_boooks = []
        for sb_index, sb in enumerate(sorted(os.listdir(songbooks_folder))):
            sb_path = os.path.join(songbooks_folder, sb)
            if not os.path.isdir(sb_path):
                continue
        
            cards = []
            for f in sorted(os.listdir(sb_path)):
                if f.startswith("~"):
                    continue
                if f.endswith("pptx"):
                    info = f.replace(".pptx", "")
                    number_of_slides = self._number_of_slides(
                        os.path.join(sb_path, f)
                    )
                    card = {
                        "sequence": info.split("-")[0].strip(),
                        "artist": info.split("-")[1].strip(),
                        "song": info.split("-")[2].strip(),
                        "images": self._presentation_to_images(
                            os.path.join(sb_path, f),
                            number_of_slides,
                            sb
                        )
                    }
                    cards.append(card)
            self.song_books.append(Songbook(
                sequence=sb.split("-")[0].strip(),
                title=sb.split("-")[1].strip(),
                cards=cards,
                index=sb_index,
                focus=False
            ))

    def initialize_home(self):

        # Create card widgets
        for sb in self.song_books:
            self.ids["home_layout"].add_widget(sb)

        # Focus first
        self.song_books[0].focus = True
        self.focused_songbook = self.song_books[0]

    def initialize_songbook(self, songbook):
        
        self.ids["songbook_layout"].clear_widgets()

        # Do we need placeholders ?
        if len(songbook.cards) < SONGBOOK_MIN_COLS_NUM * SONGBOOK_MIN_ROWS_NUM:
            to_add = SONGBOOK_MIN_COLS_NUM * SONGBOOK_MIN_ROWS_NUM - len(songbook.cards)
            self._placeholders_num = to_add
            while to_add > 0:
                songbook.cards.append(
                    {
                        "is_placeholder": True,
                        "sequence": None,
                        "artist": None,
                        "song": None,
                    }
                )
                to_add = to_add - 1
        else:
            # Need to increase grid space
            rows_needed = len(songbook.cards) // SONGBOOK_MIN_COLS_NUM
            self.ids["songbook_layout"].rows = rows_needed + 1


        # Create card widgets
        self._card_instances = []
        for index, c in enumerate(songbook.cards):
            c_instance = SongCard(
                sequence=c["sequence"],
                artist=c["artist"],
                song=c["song"],
                images=c.get("images", []),
                is_placeholder=c.get("is_placeholder", False),
                index=index,
            )
            self._card_instances.append(c_instance)
            self.ids["songbook_layout"].add_widget(c_instance)

        # Focus first card
        self._card_instances[0].set_focus()
        self.focused_card = self._card_instances[0]
        
        self.ids["prompt_layout"].all_cards = self._card_instances
        self.ids["prompt_layout"].placeholders_num = self._placeholders_num


class TeleprompterApp(App):

    # Expose constants to kivy
    SONGBOOK_MIN_ROWS_NUM = SONGBOOK_MIN_ROWS_NUM
    SONGBOOK_MIN_COLS_NUM = SONGBOOK_MIN_COLS_NUM

    Window.fullscreen = True
    Window.allow_screensaver = False

    def build(self):
        main = TeleprompterWidget()
        main.load_songbooks()
        main.current_songbook = main.song_books[0] if main.song_books else None
        main.initialize_home()
        main.set_mode("home")
        return main


if __name__ == "__main__":
    TeleprompterApp().run()
