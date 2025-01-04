import math
from typing import List, Tuple, Union, Optional, Dict

from .math import sign
from .vector import Vector2D
from .draw import SpriteBody

#########################
# collisions

def rect_collision(rect_1_tl: Tuple[float, float], rect_1_br: Tuple[float, float], rect_2_tl: Tuple[float, float], rect_2_br: Tuple[float, float]) -> bool:
    # https://silentmatt.com/rectangle-intersection/
    if rect_1_tl[0] <= rect_2_br[0] and rect_1_br[0] >= rect_2_tl[0] and rect_1_tl[1] >= rect_2_br[1] and rect_1_br[1] <= rect_2_tl[1]:
        return True
    return False

class CollisionHandler:
    def __init__(self, grid_size: float = 50) -> None:
        self.grid_size = grid_size

    def assign_grid_locations(self, sprites: List[SpriteBody]) -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], List[SpriteBody]]]:
        #  0.17 ->  0  =>  0 -> 1
        # -0.17 -> -1  => -1 -> 0
        #  8.61 ->  8  =>  8 -> 9
        # -8.61 -> -9  => -9 -> -8
        grid_positions = []
        grid_mapper = {}
        for sprite in sprites:
            sprite_position = sprite.get_collision_mesh()[0]
            grid_position = math.floor(sprite_position.x / self.grid_size), math.floor(sprite_position.y / self.grid_size)
            if not grid_position in grid_mapper:
                grid_mapper[grid_position] = []
            grid_positions.append(grid_position)
            grid_mapper[grid_position].append(sprite)
        return grid_positions, grid_mapper

    def get_adjacent_sprites(self, grid_position: Tuple[int, int], grid_mapper: Dict[Tuple[int, int], List[SpriteBody]]) -> List[SpriteBody]:
        # 0 1 2
        # 3 4 5
        # 6 7 8
        x, y = grid_position
        sprites = []
        # 0
        if (x - 1, y - 1) in grid_mapper:
            sprites += grid_mapper[(x - 1, y - 1)]
        # 1
        if (x - 1, y) in grid_mapper:
            sprites += grid_mapper[(x - 1, y)]
        # 2
        if (x - 1, y + 1) in grid_mapper:
            sprites += grid_mapper[(x - 1, y + 1)]
        # 3
        if (x, y - 1) in grid_mapper:
            sprites += grid_mapper[(x, y - 1)]
        # 4
        if (x, y) in grid_mapper:
            sprites += grid_mapper[(x, y)]
        # 5
        if (x, y + 1) in grid_mapper:
            sprites += grid_mapper[(x, y + 1)]
        # 6
        if (x + 1, y - 1) in grid_mapper:
            sprites += grid_mapper[(x + 1, y - 1)]
        # 7
        if (x + 1, y) in grid_mapper:
            sprites += grid_mapper[(x + 1, y)]
        # 8
        if (x + 1, y + 1) in grid_mapper:
            sprites += grid_mapper[(x + 1, y + 1)]
        return sprites
    
    def compute_collisions(self, sprites: List[SpriteBody]) -> None:
        grid_positions, grid_mapper = self.assign_grid_locations(sprites)
        for sprite, grid_position in zip(sprites, grid_positions):
            for target in self.get_adjacent_sprites(grid_position, grid_mapper):
                if sprite == target:
                    continue
                shape_a = sprite.get_collision_mesh()[1]
                shape_b = target.get_collision_mesh()[1]
                if rect_collision(shape_a[0].tuple(), shape_a[2].tuple(), shape_b[0].tuple(), shape_b[2].tuple()):
                    if sprite.collision_func != None:
                        sprite.collision_func(sprite, target)

#########################
# constrained body

class Node:
    def __init__(self, pos: Union[Tuple[float, float], Vector2D], tag: str) -> None:
        if not isinstance(pos, Vector2D):
            pos = Vector2D.from_tuple(pos)
        self.pos: Vector2D = pos
        self.tag: str = tag
        self.parent: Optional['Node'] = None
        self.distance_to_parent: Optional[float] = None
        self.children: List['Node'] = []
    
    def add_child(self, child: 'Node', distance_to_child: float) -> None:
        child.parent = self
        child.distance_to_parent = distance_to_child
        self.children.append(child)

    def direction_to_parent(self) -> Optional[Vector2D]:
        return (self.parent.pos - self.pos).normalize() if self.parent != None else None # CP = P - C

    def update_position_based_on_parent(self) -> None:
        direction_to_parent = self.direction_to_parent()
        if direction_to_parent != None and self.distance_to_parent != None:
            self.pos = self.parent.pos - direction_to_parent * self.distance_to_parent

class ConstrainedBody:
    def __init__(self, root_pos: Vector2D, root_tag: str, min_angle: float = 0, max_angle: float = math.pi) -> None:
        self.root = Node(root_pos, root_tag)
        self.all_nodes: Dict[str, Node] = {self.root.tag: self.root}
        self.min_angle = min_angle
        self.max_angle = max_angle

    def bfs(self, start_node: Node) -> List[Node]:
        queue = [start_node]
        viz = set()
        nodes = []
        while len(queue) > 0:
            top_node = queue.pop(0)
            if not top_node.tag in viz:
                nodes.append(top_node)
                viz.add(top_node.tag)
                for child_node in top_node.children:
                    if not child_node.tag in viz:
                        queue.append(child_node)
        return nodes
    
    def get_nodes_as_list(self) -> List[Node]:
        return self.bfs(self.root)

    def find_node_from_tag(self, tag: str) -> Optional[Node]:
        return self.all_nodes.get(tag, None)
    
    def add_node_to_parent(self, node_pos: Vector2D, node_tag: str, parent: Node) -> None:
        assert parent.tag in self.all_nodes and not node_tag in self.all_nodes
        child = Node(node_pos, node_tag)
        parent.add_child(child, parent.pos.dist(child.pos))
        self.all_nodes[node_tag] = child
    
    def move_root(self, pos: Vector2D) -> None:
        self.root.pos = pos
        self.apply_fixed_length_constraint()
        self.apply_angle_constraint(update_both_nodes=True)
        # another call to fix length (to avoid any physics bugs due to other constraints)
        # self.apply_fixed_length_constraint()

    def apply_fixed_length_constraint(self) -> None:
        for node in self.get_nodes_as_list():
            node.update_position_based_on_parent()

    def apply_angle_constraint(self, update_both_nodes: bool = False) -> None:
        for node in self.get_nodes_as_list():
            if node.parent != None and node.parent.parent != None:
                A = node.parent.parent.pos
                B = node.parent.pos
                C = node.pos
                angle = (A - B).angle(C - B)
                abs_angle = abs(angle)
                if abs_angle < self.min_angle or abs_angle > self.max_angle:
                    if abs_angle < self.min_angle:
                        delta_angle = self.min_angle - abs_angle
                        if update_both_nodes:
                            delta_angle_a = (delta_angle / 2) * -sign(angle)
                            delta_angle_b = (delta_angle / 2) * sign(angle)
                        else:
                            delta_angle_a = delta_angle * -sign(angle)
                            delta_angle_b = 0
                    else:
                        delta_angle = self.max_angle - abs_angle
                        if update_both_nodes:
                            delta_angle_a = (delta_angle / 2) * sign(angle)
                            delta_angle_b = (delta_angle / 2) * -sign(angle)
                        else:
                            delta_angle_a = delta_angle * sign(angle)
                            delta_angle_b = 0
                    node.parent.parent.pos = node.parent.parent.pos.rotate(delta_angle_a, node.parent.pos)
                    node.pos = node.pos.rotate(delta_angle_b, node.parent.pos)
