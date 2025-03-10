from typing import List, Tuple, Optional, Union, Callable

from .vector import Vector2D
from avour import Avour, COORD3INT, COORD2FLOAT

COORD = Union[COORD2FLOAT, Vector2D]
RELATION = Tuple[Vector2D, float, float] # position, angle, scale

class SpriteVertexGroup:
    def __init__(self, vertices: List[COORD] = [], color: COORD3INT = (255, 255, 255)) -> None:
        # create a vector for each vertex
        self.vertices = [v.copy() if isinstance(v, Vector2D) else Vector2D.from_tuple(v) for v in vertices]
        self.color = color
        # children: [(SVG, RELATION), (...)]
        # RELATION: defines how child is related to parent, consists of (position, angle, scale)
        self.children: List[Tuple['SpriteVertexGroup', RELATION]] = []
        # list of groups of computed vertices for all children (recursively), each group is a shape with a color
        self.vertex_groups: List[Tuple[List[Vector2D], COORD3INT]] = None
    
    # making a copy
    def copy(self, vertices: Optional[List[COORD]] = None, with_children: bool = False) -> 'SpriteVertexGroup':
        # create a copy/duplicate of the SVG, but change the vertices if required and other properties
        svg = SpriteVertexGroup(vertices if vertices != None else self.vertices)
        svg.color = self.color
        if with_children:
            svg.children = self.children
        return svg
    
    def flip_on_x(self, with_children: bool = False) -> 'SpriteVertexGroup':
        return self.copy([(-v.x, v.y) for v in self.vertices], with_children=with_children)

    def flip_on_y(self, with_children: bool = False) -> 'SpriteVertexGroup':
        return self.copy([(v.x, -v.y) for v in self.vertices], with_children=with_children)
    
    def rotate_on_center(self, angle: float, with_children: bool = False) -> 'SpriteVertexGroup':
        return self.copy([v.rotate(angle) for v in self.vertices], with_children=with_children)

    def add_group(self, child: 'SpriteVertexGroup', position: Vector2D = Vector2D.origin(), angle: float = 0.0, scale: float = 1.0) -> None:
        self.children.append((
            child, # SVG
            (position, angle, scale) # RELATION
        ))

    def compute_vertex_groups(self) -> List[Tuple[List[Vector2D], COORD3INT]]:
        # compute vertex_groups if not computed yet
        # analogy: set the vertices in stone / apply the transformations of all the children recursively and store the vertices
        if self.vertex_groups == None:
            # rotate vertex by angle
            # scale the vertex
            # move the vertex by position (gives coordinate in current axis)
            self.vertex_groups = []
            for child, (position, angle, scale) in self.children:
                for vertex_group in child.compute_vertex_groups():
                    self.vertex_groups.append((
                        [vertex.rotate(angle) * scale + position for vertex in vertex_group[0]],
                        vertex_group[1]
                    ))
            self.vertex_groups.append((
                self.vertices,
                self.color
            ))
        return self.vertex_groups

    def apply_transform(self, position: Vector2D = Vector2D.origin(), angle: float = 0.0, scale: float = 1.0, check_validity: bool = True) -> List[Tuple[List[Vector2D], COORD3INT]]:
        vertex_groups = []
        for vertex_group in self.compute_vertex_groups():
            # either check_validity is turned off
            # or if turned on, it is a valid shape (has atleast 3 vertices)
            if not check_validity or len(vertex_group[0]) >= 3:
                # convert vertex from current axis to global axis
                vertex_groups.append((
                    [vertex.rotate(angle) * scale + position for vertex in vertex_group[0]],
                    vertex_group[1]
                ))
        return vertex_groups

class SpritePrimitive:
    @staticmethod
    def rect_primitive(pos: COORD2FLOAT, width: float, height: float, from_center: bool = False) -> List[COORD2FLOAT]:
        if from_center:
            return [
                (pos[0] - width / 2, pos[1] + height / 2),
                (pos[0] + width / 2, pos[1] + height / 2),
                (pos[0] + width / 2, pos[1] - height / 2),
                (pos[0] - width / 2, pos[1] - height / 2),
            ]
        else:
            return [
                (pos[0], pos[1]),
                (pos[0] + width, pos[1]),
                (pos[0] + width, pos[1] - height),
                (pos[0], pos[1] - height),
            ]

class SpriteBody:
    def __init__(self) -> None:
        # empty svg to hold others svgs
        self.position = Vector2D.origin()
        self.angle = 0
        self.scale = 1
        self.svg = SpriteVertexGroup()
        self.collision_svg = None
        self.collision_func: Callable[['SpriteBody', 'SpriteBody'], None] = None

    # adding shapes wrt to sprite origin
    def add_rect(self, position: COORD, width: float, height: float, from_center: bool = False, color: COORD3INT = (255, 255, 255)) -> None:
        position = position if isinstance(position, Vector2D) else Vector2D.from_tuple(position)
        self.svg.add_group(
            SpriteVertexGroup(
                SpritePrimitive.rect_primitive(
                    (0, 0), width=width, height=height, from_center=from_center
                ), color=color
            ),
            position=position
        )

    def compute_collision_mesh(self) -> SpriteVertexGroup:
        if self.collision_svg == None:
            top_most = -1
            bottom_most = -1
            left_most = -1
            right_most = -1
            for shape, color in self.svg.compute_vertex_groups():
                for vertex in shape:
                    if top_most == -1 or vertex.y > top_most:
                        top_most = vertex.y
                    if bottom_most == -1 or vertex.y < bottom_most:
                        bottom_most = vertex.y
                    if left_most == -1 or vertex.x < left_most:
                        left_most = vertex.x    
                    if right_most == -1 or vertex.x > right_most:
                        right_most = vertex.x
            self.collision_svg = SpriteVertexGroup(
                [(left_most, top_most), (right_most, top_most), (right_most, bottom_most), (left_most, bottom_most)],
                color=(45, 209, 42)
            )
        return self.collision_svg

    def get_collision_mesh(self) -> Tuple[Vector2D, List[Vector2D]]:
        for shape, color in self.compute_collision_mesh().apply_transform(position=self.position, angle=self.angle, scale=self.scale, check_validity=False):
            return self.position, shape

    def draw(self, avour: Avour, show_collision_mesh: bool = True, use_sprite_color: bool = True) -> None:
        avour.push()
        avour.fill(True)
        avour.thickness(1)
        for shape, color in self.svg.apply_transform(position=self.position, angle=self.angle, scale=self.scale, check_validity=True):
            if use_sprite_color:
                avour.color(color)
            avour.polygon([vertex.tuple() for vertex in shape])
        if show_collision_mesh:
            avour.fill(False)
            avour.thickness(1)
            for shape, color in self.compute_collision_mesh().apply_transform(position=self.position, angle=self.angle, scale=self.scale, check_validity=True):
                avour.color(color)
                avour.polygon([vertex.tuple() for vertex in shape])
        avour.pop()
