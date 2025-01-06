import math
from typing import List, Tuple, Union, Optional, Dict

from .math import sign
from .vector import Vector2D
from .draw import SpriteBody, COORD3INT

BODY = Union[SpriteBody, 'RigidBody']

#########################
# generic

class RigidBody(SpriteBody):
    GRAVITY = 9.8

    def __init__(self, mass: float = 100.0, moi: float = 1_000.0) -> None:
        super().__init__()
        self.mass = mass
        self.moment_of_inertia = moi
        self.velocity = Vector2D.origin()
        self.acceleration = Vector2D.origin()
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

    def get_net_force(self) -> Tuple[Vector2D, float]:
        gravity_force = Vector2D.down(self.GRAVITY) * self.mass
        net_force = 0 # gravity_force
        torque_mag = 0
        return net_force, torque_mag

    def update(self, dt: float = 0.1) -> None:
        net_force, torque_mag = self.get_net_force()
        self.acceleration = net_force / self.mass
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.angular_acceleration = torque_mag / self.moment_of_inertia
        self.angular_velocity += self.angular_acceleration * dt
        self.angle += self.angular_velocity * dt

    @staticmethod
    def rect_body(width: float, height: float, color: COORD3INT = (255, 255, 255)) -> 'RigidBody':
        sprite = RigidBody()
        sprite.add_rect((0, 0), width, height, from_center=True, color=color)
        return sprite

#########################
# collisions

def rect_collision(rect_1_tl: Tuple[float, float], rect_1_br: Tuple[float, float], rect_2_tl: Tuple[float, float], rect_2_br: Tuple[float, float]) -> bool:
    # https://silentmatt.com/rectangle-intersection/
    if rect_1_tl[0] <= rect_2_br[0] and rect_1_br[0] >= rect_2_tl[0] and rect_1_tl[1] >= rect_2_br[1] and rect_1_br[1] <= rect_2_tl[1]:
        return True
    return False

AXIS = Tuple[Vector2D, Vector2D] # (a, d) => a + f * d (vector line equation representation)

class SAT:
    # Separating Axis Theorem to check if meshes collide
    # https://www.metanetsoftware.com/technique/tutorialA.html

    @staticmethod
    def vector_projection_on_axis(axis: AXIS, point: Vector2D) -> Vector2D:
        fac = (point - axis[0]).dot(axis[1]) / axis[1].mag_square()
        return axis[0] + axis[1] * fac
    
    @staticmethod
    def vector_projection_factor_on_axis(axis: AXIS, point: Vector2D) -> float:
        return (point - axis[0]).dot(axis[1]) / axis[1].mag_square()
    
    @staticmethod
    def factor_to_vector_on_axis(axis: AXIS, fac: float) -> Vector2D:
        return axis[0] + axis[1] * fac

    @staticmethod
    def get_axes_for_shape(shape: List[Vector2D]) -> List[AXIS]:
        axes = []
        for i in range(len(shape)):
            axes.append((
                shape[i], # a
                shape[(i + 1) % len(shape)] - shape[i] # d = a2 - a1 (a2 -> a1 + 1)
            ))
        return axes
    
    @staticmethod
    def shape_projection_on_axis(axis: AXIS, shape: List[Vector2D]) -> Tuple[float, float]:
        facs = [SAT.vector_projection_factor_on_axis(axis, point) for point in shape]
        return min(facs), max(facs)
    
    @staticmethod
    def shapes_projection_overlap_on_axis(axis: AXIS, source_shape: List[Vector2D], target_shape: List[Vector2D]) -> Tuple[float, Vector2D, Vector2D]:
        min_s, max_s = SAT.shape_projection_on_axis(axis, source_shape)
        min_t, max_t = SAT.shape_projection_on_axis(axis, target_shape)
        # overlap = max(0, min(maxa, maxb) - max(mina, minb))
        min_o, max_o = max(min_s, min_t), min(max_s, max_t) # rightmost (maximum value) min and leftmost (minmum value) max should be in order
        return max_o - min_o, SAT.factor_to_vector_on_axis(axis, min_o), SAT.factor_to_vector_on_axis(axis, max_o)

    @staticmethod
    def check_collision(source_shape: List[Vector2D], target_shape: List[Vector2D]) -> Optional[Vector2D]:
        axis_with_no_overlap = False
        min_overlap_factor = -1
        min_overlap_vectors = None
        for axis in SAT.get_axes_for_shape(source_shape) + SAT.get_axes_for_shape(target_shape):
            # project both shapes to an axis, and get their overlap (1D projection)
            overlap_factor, *o_vectors = SAT.shapes_projection_overlap_on_axis(axis, source_shape, target_shape)
            # if no overlap in even one axis, there is no collision
            if overlap_factor < 0:
                axis_with_no_overlap = True
                break
            # we need min overlap axis to decide which direction the collision is taking place
            if min_overlap_factor == -1 or overlap_factor < min_overlap_factor:
                min_overlap_factor = overlap_factor
                min_overlap_vectors = o_vectors
        if axis_with_no_overlap:
            return None
        return min_overlap_vectors[0] - min_overlap_vectors[1]

class CollisionHandler:
    GRID_SIZE = 50
    COR = 1.0 # 

    @staticmethod
    def assign_grid_locations(sprites: List[BODY]) -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], List[BODY]]]:
        #  0.17 ->  0  =>  0 -> 1
        # -0.17 -> -1  => -1 -> 0
        #  8.61 ->  8  =>  8 -> 9
        # -8.61 -> -9  => -9 -> -8
        grid_positions = []
        grid_mapper = {}
        for sprite in sprites:
            sprite_position = sprite.get_collision_mesh()[0]
            grid_position = (
                math.floor(sprite_position.x / CollisionHandler.GRID_SIZE),
                math.floor(sprite_position.y / CollisionHandler.GRID_SIZE)
            )
            if not grid_position in grid_mapper:
                grid_mapper[grid_position] = []
            grid_positions.append(grid_position)
            grid_mapper[grid_position].append(sprite)
        return grid_positions, grid_mapper

    @staticmethod
    def get_sprites_from_grid(grid_position: Tuple[int, int], grid_mapper: Dict[Tuple[int, int], List[BODY]], with_optimization: bool = True) -> List[BODY]:
        # 0 1 2
        # 3 4 5
        # 6 7 8
        # optimized version: just need to check 4, 5, 6, 7, 8
        # as the other grids are covered by the other pair
        x, y = grid_position
        sprites = []
        if not with_optimization:
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
    
    @staticmethod
    def handle_rigid_bodies(source: RigidBody, target: RigidBody, sat_axis: Vector2D) -> None:
        # handling wrt to source
        # source to target vector
        s2t_disp = target.position - source.position
        # if collision axis is in opposite direction to source->target, reverse it
        if s2t_disp.dot(sat_axis) < 0:
            sat_axis = sat_axis * -1
        # now collision axis is in direction of source->target
        source.position -= sat_axis / 2 # move source away from target
        target.position += sat_axis / 2 # move target away from source
        # only components of velocity parallel to collision axis are affected
        # so we separate them out
        v_s = source.velocity
        v_s_para = v_s.component_parallel(sat_axis)
        v_s_perp = v_s - v_s_para
        v_t = target.velocity
        v_t_para = v_t.component_parallel(sat_axis)
        v_t_perp = v_t - v_t_para
        # https://en.wikipedia.org/wiki/Coefficient_of_restitution
        num_1 = v_s_para * source.mass + v_t_para * target.mass
        num_2 = (v_t_para - v_s_para) * CollisionHandler.COR
        den = source.mass + target.mass
        v_s_para_final = (num_1 + num_2 * target.mass) / den
        v_t_para_final = (num_1 - num_2 * source.mass) / den
        # combine them again to get final velocity vectors
        v_s = v_s_para_final + v_s_perp
        v_t = v_t_para_final + v_t_perp
        source.velocity = v_s
        target.velocity = v_t

    @staticmethod
    def handle_collisions(sprites: List[BODY]) -> None:
        grid_positions, grid_mapper = CollisionHandler.assign_grid_locations(sprites)
        for source, grid_position in zip(sprites, grid_positions):
            # rather than comparing every source with every other target (N^2)
            # we narrow the search space using grid based tagging
            for target in CollisionHandler.get_sprites_from_grid(grid_position, grid_mapper, with_optimization=True):
                # skip if source and target are same
                if source == target:
                    continue
                source_shape = source.get_collision_mesh()[1]
                target_shape = target.get_collision_mesh()[1]
                # if SAT is None, there is definitely no collision
                sat_axis = SAT.check_collision(source_shape, target_shape)
                if sat_axis == None:
                    continue
                # if a collison callback function is defined, call it
                if source.collision_func != None:
                    source.collision_func(source, target)
                # if rigid body, call rigid body collision handler
                if isinstance(source, RigidBody) and isinstance(target, RigidBody):
                    CollisionHandler.handle_rigid_bodies(source, target, sat_axis)

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
