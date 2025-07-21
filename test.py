from kivy.app import App
from kivy.lang import Builder
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty, ListProperty, StringProperty, NumericProperty
import threading
import time
from kivy.clock import mainthread


class WindowManager(ScreenManager):
    pass

class WelcomeWindow(Screen):

    def generateData(self):
        data = []
        for i in range (100):
            #print(i)
            data.append(i)
        time.sleep(3)
        self.set_screen()
        return data

    def executeFunc(self):
        self.manager.current = 'Loading' # Here is where I have tried to move to loading screen while func runs
        t1 = threading.Thread(target=self.generateData)# Here is where I have tried to thread the function
        t1.start()
        #t1.join() #Here is where I have tried to wait until func finished before changing screen
        #self.manager.current = 'Final'

    @mainthread
    def set_screen(self):
        self.manager.current = 'Final'



class LoadingWindow(Screen):
    pass

class FinalWindow(Screen):
    pass

KV = '''
WindowManager:
    WelcomeWindow:
    LoadingWindow:
    FinalWindow:

<WelcomeWindow>:
    name:'Welcome'
    BoxLayout:
        Label:
            text: "JUST SOME TEXT"
        Button:
            text: "Generate Data"
            font_size: sp(30)
            size_hint: .4,.4
            on_release:
                root.executeFunc()
                #app.root.current = "Loading"
                root.manager.transition.direction = "left"

<LoadingWindow>:
    name: 'Loading'
    BoxLayout:
        Label: 
            text: "LOADING SCREEN"
        Button:
            text: "Go Back"
            on_release:
                app.root.current = "Welcome"
                root.manager.transition.direction = "right"
                
<FinalWindow>:
    name: 'Final'
    BoxLayout:
        Label: 
            text: "FINISHED"
'''''

class TestApp(App):
    def build(self):
        return Builder.load_string(KV)

TestApp().run()