# Avour

Avour is a simple wrapper on top of [pyglet](https://pyglet.readthedocs.io) that allows us to draw stuff easily in python. The code flow is inspired from [P5JS](https://p5js.org). The applications range from visualizing simulations, making games, creating UI, etc. If you are interested in quickly setting up a graphical canvas in python, this is for you.

### Example
Here is a quick code that draws a circle at the location of your mouse pointer:
```python
from avour import Avour, COORD2FLOAT

class App(Avour):
    def __init__(self):
        super().__init__(screen_title='avour app!', show_fps=True)
        # drawing loop frame rate
        self.set_frame_rate(80)
        # to center the screen grid
        screen_size = self.get_screen_size()
        self.translate((screen_size[0] / 2, screen_size[1] / 2))
        # variable to track the mouse position
        self.mouse_position = (0, 0)

    def on_keydown(self, key: str) -> None:
        # whenever you press Q or Esc, the application stops
        if key == 'Q' or key == 'ESCAPE':
            self.exit()

    def on_mousemove(self, pos: COORD2FLOAT) -> None:
        # whenever the mouse is moved, store the position
        self.mouse_position = pos

    def draw(self) -> None:
        # set the background of the screen
        # (100) is a shortform for (100, 100, 100) -> RGB / RGBA schematic
        self.background(100)

        # set the fill mode to True
        self.fill(True)
        # set the color to a shade of green
        self.color((50, 180, 30))
        # draw the circle at the mouse position with radius 50
        self.circle(self.mouse_position, 50)
        
app = App()
app.run()
```

The full documentation will be released soon!