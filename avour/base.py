# lol, avour literally taken from a random word: flavour [Sai Akarsh - 6th December 2024]
# https://pyglet.readthedocs.io/en/latest/index.html
# https://www.geeksforgeeks.org/differences-between-pyglet-and-pygame-in-python/?ref=asr14
# pip install pyglet

import math
import pyglet
from typing import Tuple, Dict, List, Union, Literal, Optional

COORD3FLOAT = Tuple[float, float, float]
COORD2FLOAT = Tuple[float, float]
COORD4INT = Tuple[int, int, int, int]
COORD3INT = Tuple[int, int, int]
COORD2INT = Tuple[int, int]
COLOR = COORD4INT
COLOR_EXTENDED = Union[int, COORD3INT, COORD4INT]
TEXT_ANCHOR_X = Literal['left', 'center', 'right']
TEXT_ANCHOR_Y = Literal['top', 'center', 'bottom', 'baseline']

def get_mapper(module):
    # get the symbol (int) to key (str) mapper, which is more user friendly
    # https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html
    # https://pyglet.readthedocs.io/en/latest/programming_guide/mouse.html
    key_mapper = {}
    for val in dir(module):
        # skip certain keys to prevent repeat keys
        if 'MOTION_' in val or 'MOD_' in val:
            continue
        attr = getattr(module, val)
        if isinstance(attr, int):
            if not attr in key_mapper: # to prevent repeat keys
                key_mapper[attr] = val
    return key_mapper
key_mapper: Dict[int, str] = get_mapper(pyglet.window.key)
mouse_mapper: Dict[int, str] = get_mapper(pyglet.window.mouse)

class AvourBatchHandler:
    """
    Automatically handle batch selection based on drawing level
    """
    def __init__(self):
        self.batches: Dict[int, Tuple[pyglet.graphics.Batch, List[pyglet.shapes.ShapeBase]]] = {}
        # the default level is 0
        self._create_batch(level=0)

    def _create_batch(self, level: int) -> None:
        assert not level in self.batches
        self.batches[level] = (
            pyglet.graphics.Batch(),
            []
        )

    def reset_batch_data(self) -> None:
        for level, (batch, objects) in self.batches.items():
            # remove existing objects from memory
            for object in objects:
                object.delete()
            
        for level in self.batches:
            # reinitalize the batches
            self.batches[level] = (
                pyglet.graphics.Batch(),
                []
            )
    
    def get_batch_for_level(self, level: int = 0) -> Tuple[pyglet.graphics.Batch, List[pyglet.shapes.ShapeBase]]:
        if not level in self.batches:
            self._create_batch(level)
        return self.batches[level]
    
    def draw(self) -> None:
        for level in sorted(self.batches.keys()):
            batch, objects = self.batches[level]
            batch.draw()

class Avour:
    """
    Pyglet and OpenGL based drawing backend
    """
    def __init__(
            self,
            screen_size: COORD2INT = (1200, 800),
            screen_title: str = '',
            show_fps: bool = False,
            show_fullscreen: bool = False,
        ) -> None:
        # create window
        self.window = pyglet.window.Window(
            width=screen_size[0],
            height=screen_size[1],
            caption=screen_title,
            fullscreen=show_fullscreen,
            file_drops=True,
        )
        self.window.switch_to() # tell pyglet that this is the current window
        if show_fps:
            # for monitoring fps and display on screen
            self.fps_display = pyglet.window.FPSDisplay(window=self.window)

        # set window event handlers (both input and others)
        self.window.on_key_press = self._on_keydown_wrapper
        self.window.on_key_release = self._on_keyup_wrapper
        self.window.on_mouse_motion = self._on_mousemove_wrapper
        self.window.on_mouse_drag = self._on_mousedrag_wrapper
        self.window.on_mouse_press = self._on_mousedown_wrapper
        self.window.on_mouse_release = self._on_mouseup_wrapper
        self.window.on_mouse_scroll = self._on_mousewheel_wrapper
        # NOTE: we directly bind on_draw() rather than schedule it
        # because, scheduling forces N calls to be made every second (leading to screen tear and shuttering black screen)
        # but if we bind it, it will automatically reduce call count (reducing frame rate) and prevents artifacts
        self.window.on_draw = self._frame_wrapper
        self.window.on_close = self.exit
        self.window.on_activate = self.on_activate
        self.window.on_deactivate = self.on_deactivate
        self.window.on_file_drop = self._on_file_drop_wrapper

        # variables
        self.show_fps = show_fps
        self.frame_rate = 60
        self.physics_rate = 120
        self._running_physics = False
        self.keys_active: Dict[str, int] = {} # to store live/active keys and press duration
        self.reset() # set draw states
        self._state_memory = [] # to store draw states
        self.batch_handler = AvourBatchHandler() # to handle multiple batches

    # world level

    def get_screen_size(self) -> COORD2INT:
        return self.window.get_size()

    def set_frame_rate(self, value: int) -> None:
        self.frame_rate = value

    def set_physics_rate(self, value: int) -> None:
        self.physics_rate = value

    def get_all_keys(self) -> List[str]:
        return sorted(list(key_mapper.values()))
    
    def get_all_mouse_buttons(self) -> List[str]:
        return sorted(list(mouse_mapper.values()))
    
    # world level - draw states

    def reset(self) -> None:
        self._color: COLOR = (0, 0, 0, 255)
        self._thickness = 1.0
        self._fill = True
        self._scale = 1.0
        self._translate: COORD2FLOAT = (0.0, 0.0)
        self._invert_y_axis = False # to invert the y axis when drawing

    def _parse_color(self, color: COLOR_EXTENDED) -> COLOR:
        if isinstance(color, int):
            return (color, color, color, 255) # Greyscale
        elif len(color) == 3:
            return (color[0], color[1], color[2], 255) # Adding alpha
        else:
            return color # RGBA

    def color(self, color: COLOR_EXTENDED) -> None:
        self._color = self._parse_color(color)

    def thickness(self, thickness: float) -> None:
        self._thickness = thickness

    def fill(self, fill: bool) -> None:
        self._fill = fill

    def scale(self, scale: float) -> None:
        self._scale = scale

    def translate(self, shift: COORD2FLOAT) -> None:
        self._translate = shift

    def invert_y_axis(self, invert: bool) -> None:
        self._invert_y_axis = invert

    def push(self, reset: bool = False) -> None:
        self._state_memory.append({
            'color': self._color,
            'thickness': self._thickness,
            'fill': self._fill,
            'scale': self._scale,
            'translate': self._translate,
            'invert_y_axis': self._invert_y_axis
        })
        if reset:
            self.reset()

    def pop(self) -> None:
        if len(self._state_memory) == 0:
            return
        states = self._state_memory.pop(-1)
        self._color = states['color']
        self._thickness = states['thickness']
        self._fill = states['fill']
        self._scale = states['scale']
        self._translate = states['translate']
        self._invert_y_axis = states['invert_y_axis']

    # internal events

    def _on_keydown_wrapper(self, symbol: int, modifiers: int) -> None:
        if not symbol in key_mapper:
            return
        self.keys_active[key_mapper[symbol]] = 0
        self.on_keydown(key=key_mapper[symbol])

    def on_keydown(self, key: str) -> None:
        pass

    def _on_keyup_wrapper(self, symbol: int, modifiers: int) -> None:
        if not symbol in key_mapper:
            return
        del self.keys_active[key_mapper[symbol]]
        self.on_keyup(key=key_mapper[symbol])

    def on_keyup(self, key: str) -> None:
        pass

    def _on_mousemove_wrapper(self, x: int, y: int, dx: float, dy: float) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        self.on_mousemove(pos=coord)

    def on_mousemove(self, pos: COORD2FLOAT) -> None:
        pass

    def _on_mousedrag_wrapper(self, x: int, y: int, dx: int, dy: int, button: int, modifiers: int) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        self.on_mousedrag(pos=coord, button=mouse_mapper[button])

    def on_mousedrag(self, pos: COORD2FLOAT, button: str) -> None:
        pass

    def _on_mousedown_wrapper(self, x: int, y: int, button: int, modifiers: int) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        self.on_mousedown(pos=coord, button=mouse_mapper[button])

    def on_mousedown(self, pos: COORD2FLOAT, button: str) -> None:
        pass

    def _on_mouseup_wrapper(self, x: int, y: int, button: int, modifiers: int) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        self.on_mouseup(pos=coord, button=mouse_mapper[button])

    def on_mouseup(self, pos: COORD2FLOAT, button: str) -> None:
        pass

    def _on_mousewheel_wrapper(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        self.on_mousewheel(coord, scroll_y)

    def on_mousewheel(self, pos: COORD2FLOAT, value: float) -> None:
        pass

    # extra internal events

    def on_activate(self):
        pass
        # print("Switched back to pyglet app")

    def on_deactivate(self):
        pass
        # print("Switched to another app")

    def _on_file_drop_wrapper(self, x: int, y: int, paths: list[str]) -> None:
        coord = self._screen_to_local_coordinates((x, y))
        if len(paths) > 0:
            self.on_file_drop(pos=coord, path=paths[0])
    
    def on_file_drop(self, pos: COORD2FLOAT, path: str) -> None:
        pass

    # main loop

    def _frame_wrapper(self) -> None:
        # resetting batch data
        self.batch_handler.reset_batch_data()

        # clearing window, making shape objects and drawing them
        self.window.clear() # clear the window
        self.draw() # user defined frame draw call to create objects
        self.batch_handler.draw() # drawing objects using batches for efficiency and control
        if self.show_fps: # draw inbuilt fps object
            self.fps_display.draw()

    def draw(self) -> None:
        pass

    def _physics_wrapper(self, dt: float) -> None:
        # handle key press duration
        for key in self.keys_active:
            self.keys_active[key] += 1
        # set running_physics to True to prevent drawing inside loop()
        self._running_physics = True
        self.loop(dt=dt)
        self._running_physics = False

    def loop(self, dt: float) -> None:
        pass

    def run(self) -> None:        
        # main loop runs at a certain interval (and calls on_draw, input event handlers for example)
        # and will also call all other schedules automatically based on their interval
        # NOTE: rather than using inbuilt on_draw(), we use _frame_wrapper() for handling the drawing
        # we directly bind it in __init__ instead of scheduling it (check comments there)
        # pyglet.clock.schedule_interval(self._frame_wrapper, 1 / self.frame_rate) # schedule frame draw call
        pyglet.clock.schedule_interval(self._physics_wrapper, 1 / self.physics_rate) # schedule physics loop call
        pyglet.app.run(1 / self.frame_rate) # main loop runs at same rate as drawing

    def exit(self) -> None:
        pyglet.app.exit()
        self.window.close()

    # drawing primitives

    def _local_to_screen_coordinates(self, val: COORD2FLOAT) -> COORD2FLOAT:
        val = val[0] * self._scale, val[1] * self._scale # scaling wrt original axis
        val = val[0] + self._translate[0], val[1] + self._translate[1] # move the coordinate axis
        val = val[0], val[1] * (-1 if self._invert_y_axis else 1) # flip y coordinate
        return val

    def _screen_to_local_coordinates(self, val: COORD2FLOAT) -> COORD2FLOAT:
        val = val[0], val[1] * (-1 if self._invert_y_axis else 1) # flip y coordinate
        val = val[0] - self._translate[0], val[1] - self._translate[1] # move the coordinate axis
        val = val[0] / self._scale, val[1] / self._scale # scaling wrt original axis
        return val
    
    def _check_inside_physics_loop(self) -> None:
        assert not self._running_physics, SyntaxError('drawing objects inside physics loop is not permitted')

    def _add_object_to_batch(self, obj: Union[pyglet.shapes.ShapeBase, pyglet.text.layout.TextLayout], level: int) -> None:
        batch, objects = self.batch_handler.get_batch_for_level(level)
        obj.batch = batch
        objects.append(obj)

    def sprite(self, image: pyglet.image.AbstractImage, pos: COORD2FLOAT, scale: float = 1.0, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        scale = scale * self._scale
        sprite = pyglet.sprite.Sprite(img=image, x=pos[0], y=pos[1])
        sprite.scale = scale
        sprite.y -= sprite.height # to make pos wrt top-left corner
        self._add_object_to_batch(
            sprite,
            level=level
        )

    def background(self, color: COLOR_EXTENDED) -> None:
        self._check_inside_physics_loop()
        color = self._parse_color(color)
        width, height = self.get_screen_size()
        self._add_object_to_batch(
            pyglet.shapes.Rectangle(0, 0, width, height, color=color),
            level=0
        )

    def text(self, text: str, pos: COORD2FLOAT, font_name: str = 'Arial', font_size: int = 20, anchor_x: TEXT_ANCHOR_X = 'left', anchor_y: TEXT_ANCHOR_Y = 'baseline', use_screen_coordinates: bool = False, bold: bool = False, italic: bool = False, multiline: bool = False, width: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        # if given pos are already in screen coordinates, dont transform
        if not use_screen_coordinates:
            pos = self._local_to_screen_coordinates(pos)
        self._add_object_to_batch(
            pyglet.text.Label(text=text, x=pos[0], y=pos[1], width=width, font_name=font_name, font_size=font_size, anchor_x=anchor_x, anchor_y=anchor_y, bold=bold, italic=italic, multiline=multiline, color=self._color),
            level=level
        )

    def line(self, start_pos: COORD2FLOAT, end_pos: COORD2FLOAT, level: int = 0) -> None:
        self._check_inside_physics_loop()
        start_pos = self._local_to_screen_coordinates(start_pos)
        end_pos = self._local_to_screen_coordinates(end_pos)
        thickness = self._thickness * self._scale
        self._add_object_to_batch(
            pyglet.shapes.Line(start_pos[0], start_pos[1], end_pos[0], end_pos[1], width=thickness, color=self._color),
            level=level
        )
    
    def lines(self, points: List[COORD2FLOAT], closed: bool = False, use_multiline: bool = False, level: int = 0) -> None:
        self._check_inside_physics_loop()
        points = [self._local_to_screen_coordinates(point) for point in points]
        thickness = self._thickness * self._scale
        if use_multiline:
            self._add_object_to_batch(
                pyglet.shapes.MultiLine(*points, closed=closed, thickness=thickness, color=self._color),
                level=level
            )
        else:
            if closed:
                points.append(points[0])
            for ind in range(len(points) - 1):
                self._add_object_to_batch(
                    pyglet.shapes.Line(points[ind][0], points[ind][1], points[ind + 1][0], points[ind + 1][1], width=thickness, color=self._color),
                    level=level
                )

    def bezier(self, points: List[COORD2FLOAT], factor: float = 1.0, segments: int = 100, level: int = 0) -> None:
        self._check_inside_physics_loop()
        points = [self._local_to_screen_coordinates(point) for point in points]
        thickness = self._thickness * self._scale
        self._add_object_to_batch(
            pyglet.shapes.BezierCurve(*points, t=factor, segments=segments, thickness=thickness, color=self._color),
            level=level
        )

    def circle(self, pos: COORD2FLOAT, radius: float, segments: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        radius = radius * self._scale
        if self._fill:
            self._add_object_to_batch(
                pyglet.shapes.Circle(pos[0], pos[1], radius, segments=segments, color=self._color),
                level=level
            )
        else:
            thickness = self._thickness * self._scale
            self._add_object_to_batch(
                pyglet.shapes.Arc(pos[0], pos[1], radius, segments=segments, start_angle=0, angle=math.tau, closed=True, thickness=thickness, color=self._color),
                level=level
            )
    
    def ellipse(self, pos: COORD2FLOAT, major: float, minor: float, segments: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        major = major * self._scale
        minor = minor * self._scale
        if self._fill:
            self._add_object_to_batch(
                pyglet.shapes.Ellipse(pos[0], pos[1], major, minor, segments=segments, color=self._color),
                level=level
            )

    def sector(self, pos: COORD2FLOAT, radius: float, angle_start: float, angle_delta: float, segments: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        radius = radius * self._scale
        self._add_object_to_batch(
            pyglet.shapes.Sector(pos[0], pos[1], radius, segments=segments, start_angle=angle_start, angle=angle_delta, color=self._color),
            level=level
        )

    def arc(self, pos: COORD2FLOAT, radius: float, angle_start: float, angle_delta: float, closed: bool = False, segments: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        radius = radius * self._scale
        thickness = self._thickness * self._scale
        self._add_object_to_batch(
            pyglet.shapes.Arc(pos[0], pos[1], radius, segments=segments, start_angle=angle_start, angle=angle_delta, closed=closed, thickness=thickness, color=self._color),
            level=level
        )
    
    def rect(self, pos: COORD2FLOAT, width: int, height: int, radius: Optional[Union[int, Tuple[int, int, int, int]]] = None, segments: int = None, level: int = 0) -> None:
        self._check_inside_physics_loop()
        pos = self._local_to_screen_coordinates(pos)
        width = width * self._scale
        height = height * self._scale
        if self._fill:
            # rect is drawn upwards wrt origin (as x goes right and y goes up), therefore we do y = y - height to counter this
            # pyglet.shapes.BorderedRectangle(pos[0], pos[1], width, height, border=3, border_color=(255, 0, 0), color=self._color, batch=self.batch)
            if radius != None:
                if isinstance(radius, tuple):
                    radius = [r * self._scale for r in radius]
                else:
                    radius = radius * self._scale
                self._add_object_to_batch(
                    pyglet.shapes.RoundedRectangle(pos[0], pos[1] - height, width, height, radius=radius, segments=segments, color=self._color),
                    level=level
                )
            else:
                self._add_object_to_batch(
                    pyglet.shapes.Rectangle(pos[0], pos[1] - height, width, height, color=self._color),
                    level=level
                )
        else:
            thickness = self._thickness * self._scale
            # we add last point as well (5 points) to make it closed manually, and we add thickness / 2 to prevent weird looking edges
            points = [(pos[0], pos[1] - height), (pos[0] + width, pos[1] - height), (pos[0] + width, pos[1]), (pos[0], pos[1]), (pos[0], pos[1] - height - thickness / 2)]
            self._add_object_to_batch(
                pyglet.shapes.MultiLine(*points, closed=False, thickness=thickness, color=self._color),
                level=level
            )

    def polygon(self, points: List[COORD2FLOAT], level: int = 0) -> None:
        self._check_inside_physics_loop()
        points = [self._local_to_screen_coordinates(point) for point in points]
        if self._fill:
            self._add_object_to_batch(
                pyglet.shapes.Polygon(*points, color=self._color),
                level=level
            )
        else:
            thickness = self._thickness * self._scale
            self._add_object_to_batch(
                pyglet.shapes.MultiLine(*points, closed=True, thickness=thickness, color=self._color),
                level=level
            )