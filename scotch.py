# random word again: scotch [Sai Akarsh - 13th December 2024]

from avour import Avour, COORD2INT
from pyglet import image

class Scotch(Avour):
    def __init__(self):
        super().__init__(screen_title='game tester', show_fps=True)
        self.set_frame_rate(80)
        self.set_physics_rate(120)
        screen_size = self.get_screen_size()
        self.translate((screen_size[0] / 2, screen_size[1] / 2))
        self.mos_pos = (0, 0)
        self.img = image.load('/Users/saiakarsh/Pictures/Screenshots/Screenshot 2024-06-05 at 5.13.33 PM.png')
        print(self.img.width, self.img.height)

    def on_keydown(self, key: str) -> None:
        if key == 'C' or key == 'ESCAPE':
            self.exit()

    def on_mousemove(self, pos):
        self.mos_pos = pos

    def on_mousedrag(self, pos: COORD2INT, button: str) -> None:
        self.mos_pos = pos

    def draw(self) -> None:
        self.background(100)

        self.fill(True)
        self.color((50, 180, 30))
        self.circle(self.mos_pos, 50)
        
        self.thickness(3)
        self.fill(False)
        self.color((150, 80, 30))
        self.polygon([self.mos_pos, (0, 0), (100, 100)])

        self.img.blit(50, 50, 0)

    def loop(self, dt: float) -> None:
        pass

sc = Scotch()
sc.run()
