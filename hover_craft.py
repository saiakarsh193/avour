from typing import Tuple
from avour import Avour
from utils.math import clip
from utils.vector import Vector2D, cross_product_3d
from utils.draw import SpriteBody, COORD

class Thruster:
    dim = (3, 8)

    def __init__(self, position: Vector2D, craft: 'Craft') -> None:
        self.position = position
        self.craft = craft
        self.max_thrust = craft.max_thrust
        self.thrust_factor = 0 # -1 to 1: 1 -> fire downwards/thrust upwards, -1 -> fire upwards/thrust downwards
        self.max_fire_height = 10
    
    def set_thrust(self, thrust_factor: float) -> None:
        self.thrust_factor = clip(thrust_factor, -1 , 1)

    def get_thrust_vector(self) -> Vector2D:
        # if thrust_factor > 0 => thrust upwards (fire downwards)
        # if thrust_factor < 0 => thrust downwards (fire upwards)
        return Vector2D.up(self.thrust_factor * self.max_thrust).rotate(self.craft.angle, Vector2D.origin())
    
    def get_position_vector(self) -> Vector2D:
        return self.position.rotate(self.craft.angle, Vector2D.origin()) + self.craft.position

    def draw_fire(self, avour: Avour) -> None:
        avour.fill(True)
        avour.color((255, 0, 0))
        avour.thickness(1)
        st = self.get_position_vector()
        # negative to get fire direction, normalize and multiply with max_fire_height
        thrust_direction = -self.get_thrust_vector().normalize(ignore_zero_mag=True) * abs(self.thrust_factor) * self.max_fire_height
        en = st + thrust_direction
        avour.line(st.tuple(), en.tuple())

class Craft:
    def __init__(self, position: COORD = (0, 0)) -> None:
        # constants
        self.gravity = 9.8
        self.mass = 100.0
        self.moment_of_inertia = 50_000.0
        self.max_thrust = 2500.0

        # variables
        self.position = position if isinstance(position, Vector2D) else Vector2D.from_tuple(position)
        self.velocity = Vector2D.origin()
        self.acceleration = Vector2D.origin()
        self.angle = 0.0 # 0 -> PI
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0
        self.on_ground = False

        # dimensions
        self.main_frame_dim = (50, 4)
        self.main_frame_thruster_distance = 0.8 * (self.main_frame_dim[0] / 2)
        
        # thrusters
        self.thruster_left = Thruster(Vector2D.left(self.main_frame_thruster_distance), self)
        self.thruster_right = Thruster(Vector2D.right(self.main_frame_thruster_distance), self)

        # sprite handler
        self.sprite = SpriteBody()
        self.sprite.add_rect(Vector2D.origin(), self.main_frame_dim[0], self.main_frame_dim[1], from_center=True, color=(255, 255, 255))
        self.sprite.add_rect(Vector2D.left(self.main_frame_thruster_distance), Thruster.dim[0], Thruster.dim[1], from_center=True, color=(150, 150, 150))
        self.sprite.add_rect(Vector2D.right(self.main_frame_thruster_distance), Thruster.dim[0], Thruster.dim[1], from_center=True, color=(150, 150, 150))

    def draw(self, avour: Avour) -> None:
        self.sprite.set(position=self.position, angle=self.angle)
        self.sprite.draw(avour, show_collision_mesh=False)
        self.thruster_left.draw_fire(avour)
        self.thruster_right.draw_fire(avour)

    def set_input(self, up: int = 0, down: int = 0, clockwise: int = 0, anticlockwise: int = 0) -> None:
        # max_reaction_frames: max value of instruction to hit 1
        max_reaction_frames = 20
        up = clip(up / max_reaction_frames, 0, 1)
        down = clip(down / max_reaction_frames, 0, 1)
        clockwise = clip(clockwise / max_reaction_frames, 0, 1)
        anticlockwise = clip(anticlockwise / max_reaction_frames, 0, 1)
        # reset, incase of inactive input
        self.thruster_left.set_thrust(0)
        self.thruster_right.set_thrust(0)
        if up > 0:
            self.thruster_left.set_thrust(up)
            self.thruster_right.set_thrust(up)
        if down > 0:
            self.thruster_left.set_thrust(-down)
            self.thruster_right.set_thrust(-down)
        if clockwise > 0:
            self.thruster_left.set_thrust(clockwise)
            self.thruster_right.set_thrust(-clockwise)
        if anticlockwise > 0:
            self.thruster_left.set_thrust(-anticlockwise)
            self.thruster_right.set_thrust(anticlockwise)

    def get_net_force(self) -> Tuple[Vector2D, float]:
        # add both thruster forces
        thrust_force = self.thruster_left.get_thrust_vector() + self.thruster_right.get_thrust_vector()
        # gravity only if not on ground
        gravity_force = Vector2D.down(self.gravity if not self.on_ground else 0) * self.mass
        # add both forces to get net force
        net_force = thrust_force + gravity_force

        # torque = dist X force (we only need z component)
        torque_mag_left = cross_product_3d((self.thruster_left.get_position_vector() - self.position).tuple_3d(), self.thruster_left.get_thrust_vector().tuple_3d())[2]
        torque_mag_right = cross_product_3d((self.thruster_right.get_position_vector() - self.position).tuple_3d(), self.thruster_right.get_thrust_vector().tuple_3d())[2]
        # add both torque components
        torque_mag = torque_mag_left + torque_mag_right
        return net_force, torque_mag

    def update(self, dt: float = 0.1) -> None:
        net_force, torque_mag = self.get_net_force()
        self.acceleration = net_force / self.mass
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.angular_acceleration = torque_mag / self.moment_of_inertia
        self.angular_velocity += self.angular_acceleration * dt
        self.angle += self.angular_velocity * dt

class HoverCraft(Avour):
    def __init__(self):
        super().__init__(screen_title='hover craft', show_fps=True)
        self.craft = Craft()
        screen_size = self.get_screen_size()
        self.translate((screen_size[0] / 2, screen_size[1] / 2))
        self.scale(4)
        self.set_frame_rate(60)
        self.set_physics_rate(100)

    def on_keydown(self, key: str) -> None:
        if key == 'ESCAPE':
            self.exit()

    def draw(self) -> None:
        self.background(100)
        self.craft.draw(self)
    
    def loop(self, dt: float) -> None:
        self.craft.set_input(
            up=self.keys_active.get('W', 0),
            down=self.keys_active.get('S', 0),
            clockwise=self.keys_active.get('Q', 0),
            anticlockwise=self.keys_active.get('E', 0),
        )
        self.craft.update(dt=dt)

hc = HoverCraft()
hc.run()
