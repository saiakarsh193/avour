from typing import Literal, List, Tuple, Optional
from avour import Avour, COORD2FLOAT
from avour.utils.vector import Vector2D
from avour.utils.math import cubic_bezier

class Node:
    NODE_TYPE = Literal['center', 'left', 'right']
    def __init__(self, pos: Vector2D, anchor: 'Anchor', ntype: NODE_TYPE) -> None:
        self.pos = pos
        self.anchor = anchor
        self.ntype = ntype
    
class Anchor:
    def __init__(self, center: Vector2D, arm_len: float, previous_anchor: Optional['Anchor'] = None) -> None:
        dir_v = Vector2D(1, 0) if previous_anchor == None else (center - previous_anchor.center.pos).normalize()
        self.center = Node(pos=center, anchor=self, ntype='center')
        self.left = Node(pos=(center - dir_v * arm_len), anchor=self, ntype='left')
        self.right = Node(pos=(center + dir_v * arm_len), anchor=self, ntype='right')

class App(Avour):
    MODES = Literal['move', 'add', 'delete'] # mode for using the spline editor
    NUM_SEGMENTS = 20 # number of segments for curve
    LENGTH_ARM = 50 # distance between center and support node (arm length)
    RADIUS_CENTER = 10 # radius of center node
    RADIUS_SUPPORT = 6 # radius of support node
    
    def __init__(self) -> None:
        super().__init__(screen_title='cublic_splines', screen_size=(800, 800), show_fps=True)
        self.mode: App.MODES = 'add'
        self.hide_nodes: bool = False
        self.anchors: List[Anchor] = []
        self.node_drag: Node = None
        self.set_frame_rate(30)

    def closest_node(self, pos: Vector2D) -> Tuple[Node, float]:
        c_node, c_dis = None, -1
        for anchor in self.anchors:
            for node in [anchor.center, anchor.left, anchor.right]:
                dis = pos.dist(node.pos)
                if c_dis == -1 or dis < c_dis:
                    c_node, c_dis = node, dis
        return c_node, c_dis
    
    def on_keydown(self, key: str) -> None:
        if key == 'ESCAPE':
            self.exit()
        elif key == 'M':
            self.mode = 'move'
        elif key == 'A':
            self.mode = 'add'
        elif key == 'D':
            self.mode = 'delete'
        elif key == 'H':
            self.hide_nodes = not self.hide_nodes

    def on_mousedown(self, pos: COORD2FLOAT, button: str) -> None:
        if button == 'LEFT':
            coord = Vector2D.from_tuple(pos)
            c_node, c_dis = self.closest_node(coord)
            if self.mode == 'add':
                if c_node == None or (c_node != None and c_dis > 2.5 * self.RADIUS_CENTER):
                    self.anchors.append(Anchor(
                        center=coord,
                        arm_len=self.LENGTH_ARM,
                        previous_anchor=self.anchors[-1] if len(self.anchors) > 0 else None
                    ))
            elif self.mode == 'delete':
                if c_node != None and c_node.ntype == 'center' and c_dis < self.RADIUS_CENTER:
                    self.anchors.remove(c_node.anchor)
            elif self.mode == 'move':
                if self.node_drag == None and c_node != None:
                    if (c_node.ntype == 'center' and c_dis < self.RADIUS_CENTER) or (c_node.ntype != 'center' and c_dis < self.RADIUS_SUPPORT):
                        self.node_drag = c_node

    def on_mouseup(self, pos: COORD2FLOAT, button: str) -> None:
        if button == 'LEFT':
            self.node_drag = None
    
    def on_mousedrag(self, pos: COORD2FLOAT, button: str) -> None:
        if self.node_drag == None:
            return
        coord = Vector2D.from_tuple(pos)
        anchor = self.node_drag.anchor
        if self.node_drag.ntype == 'center':
            delta = coord - self.node_drag.pos
            anchor.center.pos += delta
            anchor.left.pos += delta
            anchor.right.pos += delta
        else:
            dir_v = (coord - anchor.center.pos).normalize()
            if self.node_drag.ntype == 'left':
                anchor.left.pos = anchor.center.pos + dir_v * self.LENGTH_ARM
                anchor.right.pos = anchor.center.pos - dir_v * self.LENGTH_ARM
            else:
                anchor.right.pos = anchor.center.pos + dir_v * self.LENGTH_ARM
                anchor.left.pos = anchor.center.pos - dir_v * self.LENGTH_ARM
                    
    def draw(self) -> None:
        self.background(50)

        # mode text
        self.color(255)
        screen_size = self.get_screen_size()
        self.text(self.mode.upper(), (screen_size[0] - 20, screen_size[1] - 40), anchor_x='right', font_name='Comic Sans MS', font_size=20)

        self.fill(True)
        if not self.hide_nodes:
            # anchor and nodes
            for anchor in self.anchors:
                self.color(255)
                self.circle(anchor.center.pos.tuple(), self.RADIUS_CENTER)
                self.circle(anchor.left.pos.tuple(), self.RADIUS_SUPPORT)
                self.circle(anchor.right.pos.tuple(), self.RADIUS_SUPPORT)
                self.color(150)
                self.thickness(2)
                self.line(anchor.center.pos.tuple(), anchor.left.pos.tuple())
                self.line(anchor.center.pos.tuple(), anchor.right.pos.tuple())

        # curves
        for i in range(1, len(self.anchors)):
            curve_points = cubic_bezier(
                self.anchors[i - 1].center.pos.tuple(),
                self.anchors[i - 1].right.pos.tuple(),
                self.anchors[i].left.pos.tuple(),
                self.anchors[i].center.pos.tuple(),
                n_segments=self.NUM_SEGMENTS
            )
            self.color(150)
            if not self.hide_nodes:
                self.thickness(1)
            else:
                self.thickness(4)
            self.lines(curve_points)
            self.color(255)
            if not self.hide_nodes:
                for point in curve_points:
                    self.circle(point, 2)
            
app = App()
app.run()
