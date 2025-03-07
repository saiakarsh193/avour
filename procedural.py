import math
from avour import Avour, COORD2FLOAT
from avour.utils.vector import Vector2D
from avour.utils.physics import ConstrainedBody
from avour.utils.math import smoothen_tuples

class Snake:
    def __init__(self) -> None:
        self.segment_radius = [30, 35, 40, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 28, 25, 25, 22, 22, 20, 20, 20, 20, 20, 20, 18, 18, 16, 16, 14, 14, 12, 12, 10, 10]
        self.body = ConstrainedBody(root_pos=Vector2D(0, 100), root_tag='0', min_angle=0.8 * math.pi)
        for ind in range(1, len(self.segment_radius)):
            parent_seg = self.body.find_node_from_tag(str(ind - 1))
            segment_pos = parent_seg.pos + Vector2D.right(self.segment_radius[ind])
            self.body.add_node_to_parent(segment_pos, str(ind), parent_seg)
        self.segment_smoothness_factor = 4

    def draw(self, avour: Avour) -> None:
        avour.color((255, 255, 255))
        avour.fill(False)
        
        # composition
        for node in self.body.get_nodes_as_list():
            avour.circle(node.pos.tuple(), self.segment_radius[int(node.tag)])
            if node.tag != '0':
                avour.line(node.pos.tuple(), node.parent.pos.tuple())

        # outline
        bot_line = []
        top_line = []
        for node in self.body.get_nodes_as_list():
            seg_dir = node.children[0].direction_to_parent() if node.tag == '0' else node.direction_to_parent()
            vec_dir = seg_dir * self.segment_radius[int(node.tag)] + node.pos
            vec_dir = vec_dir.rotate(math.pi / 2, node.pos)
            bot_line.append(vec_dir.tuple())
            vec_dir = vec_dir.rotate(-math.pi, node.pos)
            top_line.append(vec_dir.tuple())
        # face and tail (closure of outline)
        segs = 6
        face_line = []
        root_node = self.body.root
        vec_dir = root_node.children[0].direction_to_parent() * self.segment_radius[0] + root_node.pos
        vec_dir = vec_dir.rotate(-math.pi / 2, root_node.pos)
        for _ in range(segs + 1):
            face_line.append(vec_dir.tuple())
            vec_dir = vec_dir.rotate(math.pi / segs, root_node.pos)
        tail_line = []
        tail_node = self.body.find_node_from_tag(str(len(self.segment_radius) - 1))
        vec_dir = -tail_node.direction_to_parent() * self.segment_radius[-1] + tail_node.pos
        vec_dir = vec_dir.rotate(-math.pi / 2, tail_node.pos)
        for _ in range(segs + 1):
            tail_line.append(vec_dir.tuple())
            vec_dir = vec_dir.rotate(math.pi / segs, tail_node.pos)
        # smoothening the lines generated
        face_line = smoothen_tuples(face_line, self.segment_smoothness_factor)
        tail_line = smoothen_tuples(tail_line, self.segment_smoothness_factor)
        bot_line = smoothen_tuples(bot_line, self.segment_smoothness_factor)
        top_line = smoothen_tuples(top_line, self.segment_smoothness_factor)
        avour.lines(face_line)
        avour.lines(tail_line)
        avour.lines(bot_line)
        avour.lines(top_line)

    def move(self, pos: COORD2FLOAT) -> None:
        self.body.move_root(Vector2D.from_tuple(pos))

class App(Avour):
    def __init__(self) -> None:
        super().__init__(screen_title='procedural snake', show_fps=True)
        screen_size = self.get_screen_size()
        self.translate((screen_size[0] / 2, screen_size[1] / 2))
        self.snake = Snake()

    def draw(self) -> None:
        self.background((50, 50, 50))
        self.snake.draw(self)

    def on_keydown(self, key: str) -> None:
        if key == 'Q' or key == 'ESCAPE':
            self.exit()

    def on_mousemove(self, pos: COORD2FLOAT) -> None:
        self.snake.move(pos)

app = App()
app.run()