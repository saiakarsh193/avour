import time
import math
import random
from typing import Tuple, List, Dict

from avour import Avour
from utils.vector import Vector2D, cross_product_3d
from utils.math import mapper_1d as mapper, clip, sign

COORD = Tuple[float, float]

class Grapher:
    def __init__(self, metrics: List[Tuple[str, float, float]], min_update_time: float = 100) -> None:
        self.metrics = {}
        for metric, vmin, vmax in metrics:
            self.metrics[metric] = {
                'vmin': vmin,
                'vmax': vmax,
                'data': []
            }
        self.metrics['_time'] = {'vmin': 0, 'vmax': -1, 'data': []}
        self.min_update_time = min_update_time / 1000 # milliseconds -> seconds
        self.last_update_time = time.time()
        self.max_samples_stored = 100
        self.font = PygameBackend.make_font('helveticaneue', 12)

    def log(self, data: Dict[str, float], default_value: float = 0.0) -> bool:
        current_time = time.time()
        if current_time - self.last_update_time > self.min_update_time:
            data['_time'] = current_time
            for metric in self.metrics:
                self.metrics[metric]['data'].append(data[metric] if metric in data else default_value)
                if len(self.metrics[metric]['data']) > self.max_samples_stored:
                    self.metrics[metric]['data'].pop(0)
            self.last_update_time = current_time
            return True
        return False

    def draw(self, pyg: PygameBackend) -> None:
        graph_width, graph_heigth = 200, 100
        cur_x = pyg.SCREEN_SIZE[0] // 2 - (graph_width + 30)
        cur_y = -pyg.SCREEN_SIZE[1] // 2 + 30
        for metric in self.metrics:
            vmin, vmax, data = self.metrics[metric]['vmin'], self.metrics[metric]['vmax'], self.metrics[metric]['data']
            if vmin >= vmax:
                continue
            pyg.color((255, 255, 255))
            pyg.text(metric, (cur_x + graph_width // 2, cur_y), mode='center-bottom', font=self.font)
            pyg.text(f'{vmax:d}', (cur_x, cur_y), mode='right-top', font=self.font)
            pyg.text(f'{vmin:d}', (cur_x, cur_y + graph_heigth), mode='right-bottom', font=self.font)
            pyg.color((40, 40, 40))
            pyg.rect((cur_x, cur_y), graph_width, graph_heigth, fill=True)
            ind_adjust_factor = self.max_samples_stored - len(data)
            points = []
            for ind, val in enumerate(data):
                points.append((
                    mapper(ind + ind_adjust_factor, 0, self.max_samples_stored - 1, cur_x, cur_x + graph_width),
                    mapper(clip(val, vmin, vmax), vmin, vmax, cur_y + graph_heigth, cur_y),
                ))
            pyg.color((255, 255, 255))
            pyg.lines(points)
            cur_y += graph_heigth + 30

class VectorSpriteGroup:
    def __init__(self, points: List[COORD]) -> None:
        self.points = points

    def transform(self, origin: Vector2D = Vector2D.origin(), angle: float = 0, pivot: Vector2D = Vector2D.origin()) -> 'VectorSpriteGroup':
        points = []
        for point in self.points:
            # translate
            point = (point[0] + origin.x, point[1] + origin.y)
            # rotate
            point = (point[0] - pivot.x, point[1] - pivot.y)
            point = (point[0] * math.cos(angle) - point[1] * math.sin(angle), point[0] * math.sin(angle) + point[1] * math.cos(angle))
            point = (point[0] + pivot.x, point[1] + pivot.y)
            points.append(point)
        return VectorSpriteGroup(points)
    
class Rocket:
    def __init__(self, pos: COORD = (0, 0)) -> None:
        # static
        self.gravity = 9.8
        self.mass = 100.0
        self.moment_of_inertia = 30000.0
        self.max_thrust = 2500.0
        self.max_nozzle_angle = math.pi / 8
        
        # physical properties
        self.position = Vector2D.from_tuple(pos)
        self.velocity = Vector2D.origin()
        self.acceleration = Vector2D.origin()
        self.angle = 0.0 # 0 -> PI
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        # dynamic properties
        self.thrust_factor = 0.0 # 0 -> 1 factor denoting fraction of thrust/throttle
        self.nozzle_factor = 0.0 # -1 -> 1 (-1: nozzle pointing leftwards: anticlockwise, 1: nozzle pointing rightwards: clockwise)
        self.on_ground = False

        # dimensions
        self.width = 25
        self.height = 120
        self.cone_height = 15
        self.nozzle_width_small = 10
        self.nozzle_width_big = 16
        self.nozzle_height = 10
        self.thrust_scaling = 50

        # sprite setup
        self.sprite_rocket_body = VectorSpriteGroup([
            (-self.width / 2, self.height / 2),
            (0, self.height / 2 + self.cone_height),
            (self.width / 2, self.height / 2),
            (self.width / 2, -self.height / 2),
            (-self.width / 2, -self.height / 2),
        ])
        self.sprite_rocket_nozzle = VectorSpriteGroup([
            (self.nozzle_width_small / 2, 0),
            (self.nozzle_width_big / 2, -self.nozzle_height),
            (-self.nozzle_width_big / 2, -self.nozzle_height),
            (-self.nozzle_width_small / 2, 0),
        ])

        # tracking flight data
        self.flight_data = Grapher([
            ('position_y', 0, 100),
            ('velocity_y', -100, 100),
            ('acceleration_y', -30, 30),
            ('ang_velocity', -6, 6),
            ('ang_acceleration', -4, 4)
        ])

    def get_height_from_center(self) -> float:
        return self.height / 2 + self.nozzle_height
    
    def get_thrust_sprite(self) -> VectorSpriteGroup:
        fire_height = self.thrust_factor * self.thrust_scaling
        return VectorSpriteGroup([
            (-self.nozzle_width_big / 2, 0),
            (-self.nozzle_width_big / 2, -fire_height),
            (self.nozzle_width_big / 2, -fire_height),
            (self.nozzle_width_big / 2, 0),
        ])
        
    def get_flare_sprites(self) -> List[VectorSpriteGroup]:
        flares = []
        flare_div = 5
        flare_count = 2
        flare_width = self.nozzle_width_big / flare_div
        fire_height = self.thrust_factor * self.thrust_scaling
        for flare_ind in random.sample(range(flare_div), k=flare_count):
            x_offset = mapper(flare_ind, 0, flare_div, -self.nozzle_width_big / 2, self.nozzle_width_big / 2)
            flares.append(VectorSpriteGroup([
                (x_offset, 0),
                (x_offset, -fire_height),
                (x_offset + flare_width, -fire_height),
                (x_offset + flare_width, 0)
            ]))
        return flares
    
    def draw(self, pyg: PygameBackend) -> None:
        # rocket nozzle
        pyg.color((100, 100, 100))
        nozzle_top = self.position + Vector2D.down(self.height / 2)
        nozzle_angle_local = self.max_nozzle_angle * self.nozzle_factor
        sprite_rocket_nozzle = self.sprite_rocket_nozzle.transform(angle=nozzle_angle_local)
        pyg.polygon(sprite_rocket_nozzle.transform(origin=nozzle_top, angle=self.angle, pivot=self.position).points)
        # rocket body
        pyg.color((220, 220, 220))
        pyg.polygon(self.sprite_rocket_body.transform(origin=self.position, angle=self.angle, pivot=self.position).points)
        
        # main thrust
        pyg.color((255, 151, 23))
        nozzle_base = nozzle_top + Vector2D.down(self.nozzle_height).rotate(nozzle_angle_local, origin=Vector2D.origin())
        nozzle_base = nozzle_base.rotate(self.angle, self.position)
        pyg.polygon(self.get_thrust_sprite().transform(origin=nozzle_base, angle=(self.angle + nozzle_angle_local), pivot=nozzle_base).points)
        
        # flares
        pyg.color((255, 101, 40))
        for flare in self.get_flare_sprites():
            pyg.polygon(flare.transform(origin=nozzle_base, angle=(self.angle + nozzle_angle_local), pivot=nozzle_base).points)

    def draw_guides(self, pyg: PygameBackend) -> None:
        # dots
        pyg.color((255, 0, 0))
        pyg.circle(self.position.tuple(), 2)

        # vectors
        pyg.color((0, 200, 0))
        nozzle_base = (self.position + Vector2D.down(self.get_height_from_center())).rotate(self.angle, self.position)
        dir_vec = nozzle_base + self._gravity_force / self.mass
        pyg.line(nozzle_base.tuple(), dir_vec.tuple(), width=1.5)

        pyg.color((0, 0, 200))
        dir_vec = nozzle_base + self._thrust_force / self.mass
        pyg.line(nozzle_base.tuple(), dir_vec.tuple(), width=1.5)

        pyg.color((200, 0, 0))
        dir_vec = nozzle_base + self._net_force / self.mass
        pyg.line(nozzle_base.tuple(), dir_vec.tuple(), width=1.5)

    def draw_HUD(self, pyg: PygameBackend) -> None:
        # drawing the thrust bar
        thrust_bar_width = 30
        thrust_bar_height = 120
        thrust_bar_pos = (-pyg.SCREEN_SIZE[0] / 2 + 10, pyg.SCREEN_SIZE[1] / 2 - thrust_bar_height - 10)
        pyg.color((255, 255, 255))
        pyg.rect(thrust_bar_pos, thrust_bar_width, thrust_bar_height)
        # drawing the inner thrust bar
        thrust_bar_width_inner = 20
        thrust_bar_pad = (thrust_bar_width - thrust_bar_width_inner) / 2
        thrust_bar_height_inner = thrust_bar_height - thrust_bar_pad * 2
        thrust_bar_height_map = mapper(self.thrust_factor, 0, 1, 0, thrust_bar_height_inner)
        pyg.color((155, 155, 155))
        pyg.rect((thrust_bar_pos[0] + thrust_bar_pad, thrust_bar_pos[1] + thrust_bar_pad + thrust_bar_height_inner - thrust_bar_height_map), thrust_bar_width_inner, thrust_bar_height_map)

        # orientation sphere
        orientation_sphere_radius = 50
        orientation_sphere_pos = (pyg.SCREEN_SIZE[0] / 2 - orientation_sphere_radius - 15, pyg.SCREEN_SIZE[1] / 2 - orientation_sphere_radius - 15)
        pyg.color((155, 155, 155))
        pyg.circle(orientation_sphere_pos, orientation_sphere_radius, fill=True)
        # orientation sphere thrust
        pyg.color((255, 0, 0))
        pyg.arc(orientation_sphere_pos, orientation_sphere_radius, angle_start=math.pi, angle_stop=mapper(self.thrust_factor, 0, 1.01, 0, 2 * math.pi) + math.pi, width=4)
        # orientation sphere needle pointer
        os_pos = Vector2D.from_tuple(orientation_sphere_pos)
        # NOTE: angle is negative as invert y axis off for this function => rotation will reverse when y axis is not inverted
        os_direction = VectorSpriteGroup([(-5, -20), (5, -20), (5, 25), (-5, 25)]).transform(angle=-self.angle, pivot=Vector2D.origin()).transform(origin=os_pos) # for nozzle
        pyg.color((55, 55, 55))
        pyg.polygon(os_direction.points)
        os_direction = VectorSpriteGroup([(-5, -20), (5, -20), (5, 20), (-5, 20)]).transform(angle=-self.angle, pivot=Vector2D.origin()).transform(origin=os_pos)
        pyg.color((255, 255, 255))
        pyg.polygon(os_direction.points)

    def draw_telemetry_as_text(self, pyg: PygameBackend) -> None:
        pyg.color((255, 255, 255))
        text_pos = (-pyg.SCREEN_SIZE[0] / 2 + 10, -pyg.SCREEN_SIZE[1] / 2 + 20)
        telemetry = [
            f'p: {self.position.x:.1f}, {self.position.y:.1f} m',
            f'v: {self.velocity.x:.1f}, {self.velocity.y:.1f} m/s',
            f'a: {self.acceleration.x:.1f}, {self.acceleration.y:.1f} m/s2',
            f'Ø: {self.angle:.1f} rad',
            f'W: {self.angular_velocity:.1f} rad/s',
            f'å: {self.angular_acceleration:.1f} rad/s2',
            f'T: {self.thrust_factor:.1f}',
            f'N: {self.nozzle_factor:.1f}',
            f'on_g: {self.on_ground}',
        ]
        for ind, tel in enumerate(telemetry):
            pyg.text(tel, (text_pos[0], text_pos[1] + ind * 22), mode='left') 

    def set_input(self, forward: bool = False, backward: bool = False, nozzle_left: bool = False, nozzle_right: bool = False) -> None:
        if forward:
            self.thrust_factor = min(self.thrust_factor + 0.05, 1)
        elif backward:
            self.thrust_factor = max(self.thrust_factor - 0.04, 0)
        if nozzle_left:
            self.nozzle_factor = max(self.nozzle_factor - 0.05, -1) # nozzle left (negative) -> nozzle clockwise => rocket anticlockwise
        elif nozzle_right:
            self.nozzle_factor = min(self.nozzle_factor + 0.05, 1) # nozzle right (positive) -> nozzle anticlockwise => rocket clockwise

    def get_net_force(self) -> Tuple[Vector2D, float]:
        nozzle_angle = self.angle + (self.max_nozzle_angle * self.nozzle_factor) # nozzle angle wrt ground = rocket angle wrt to ground + nozzle angle wrt to rocket
        thrust_force = Vector2D.up(self.thrust_factor * self.max_thrust).rotate(nozzle_angle, Vector2D.origin()) # thrust force is opposite to that of nozzle force
        gravity_force = Vector2D.down(self.gravity if not self.on_ground else 0) * self.mass # gravity only if not on ground
        net_force = thrust_force + gravity_force
        torque_vec = Vector2D.down(self.height / 2 + self.nozzle_height).rotate(self.angle, Vector2D.origin()) # distance vector from center to point of thrust force
        torque_mag = cross_product_3d(torque_vec.tuple_3d(), thrust_force.tuple_3d())[2] # torque = dist X force (we only need z component)
        # NOTE: REMOVE later -> setters for draw_guides()
        self._thrust_force, self._gravity_force, self._net_force = thrust_force, gravity_force, net_force
        return net_force, torque_mag
    
    def update(self, dt: float = 0.1) -> None:
        net_force, torque_mag = self.get_net_force()
        self.acceleration = net_force / self.mass
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.angular_acceleration = torque_mag / self.moment_of_inertia
        self.angular_velocity += self.angular_acceleration * dt
        self.angle += self.angular_velocity * dt

        self.flight_data.log({'position_y': self.position.y, 'velocity_y': self.velocity.y, 'acceleration_y': self.acceleration.y, 'ang_acceleration': self.angular_acceleration, 'ang_velocity': self.angular_velocity})

class LaunchPad:
    def __init__(self, pos: COORD = (0, 0), screen_width: int = 1000) -> None:
        self.position = Vector2D.from_tuple(pos)
        self.pad_width = 100
        self.pad_height = 15
        self.ground_level = self.position.y - self.pad_height
        self.sprite_pad = VectorSpriteGroup([
            (-self.pad_width / 2, 0),
            (self.pad_width / 2, 0),
            (self.pad_width / 2, -self.pad_height),
            (-self.pad_width / 2, -self.pad_height)
        ])
        self.sprite_ground = VectorSpriteGroup([
            (-screen_width / 2, -self.pad_height),
            (screen_width / 2, -self.pad_height)
        ])

    def set_rocket_on_ground(self, rocket: Rocket) -> None:
        rocket.velocity = Vector2D.origin()
        rocket.position.x = self.position.x
        rocket.position.y = self.position.y + rocket.get_height_from_center()
        rocket.angular_velocity = 0
        rocket.angle = 0
        rocket.nozzle_factor = 0

    def check_and_set_rocket_on_ground(self, rocket: Rocket) -> None:
        if rocket.position.y - rocket.get_height_from_center() <= self.position.y:
            self.set_rocket_on_ground(rocket)
            rocket.on_ground = True
        else:
            rocket.on_ground = False
    
    def draw(self, pyg: PygameBackend) -> None:
        pyg.color((255, 255, 255))
        pyg.polygon(self.sprite_pad.transform(origin=self.position).points)
        pyg.color((255, 255, 255))
        pyg.lines(self.sprite_ground.transform(origin=self.position).points)

class RocketState:
    def __init__(self, rocket: Rocket) -> None:
        self.mass = rocket.mass
        self.gravity = rocket.gravity
        self.max_thrust = rocket.max_thrust

        self.position = rocket.position.copy()
        self.velocity = rocket.velocity.copy()
        self.acceleration = rocket.acceleration.copy()
        self.angle = rocket.angle
        self.angular_velocity = rocket.angular_velocity
        self.angular_acceleration = rocket.angular_acceleration
        self.thrust_factor = rocket.thrust_factor
        self.nozzle_factor = rocket.nozzle_factor
        self.on_ground = rocket.on_ground

class GuidanceCommand:
    DISTANCE_THRESHOLD = 0.05
    VELOCITY_THRESHOLD = 0.02
    ANGLE_THRESHOLD = 0.07

    def __init__(self) -> None:
        self.is_done = False

    def draw(self, pyg: PygameBackend) -> None:
        pass

    def run(self, state: RocketState) -> Tuple[float, float]:
        return 0, 0

class HoverAtCommand(GuidanceCommand):
    def __init__(self, target_position: Vector2D) -> None:
        super().__init__()
        self.target_y = target_position.y
    
    def draw(self, pyg: PygameBackend) -> None:
        pyg.color((0, 200, 0))
        pyg.circle((0, self.target_y), 2)

    def run(self, state: RocketState) -> Tuple[float, float]:
        thrust_force = 0
        nozzle_angle = 0
        dist = self.target_y - state.position.y
        # reached destination and rocket is stationary, now need to hover continously
        if abs(dist) < self.DISTANCE_THRESHOLD and abs(state.velocity.y) < self.VELOCITY_THRESHOLD:
            thrust_force = state.mass * state.gravity
            adjust_factor = 0.001
            # slight adjustments (slightly reduce thrust if velocity is upwards, otherwise slightly increase it)
            adjust_thrust_force = thrust_force * adjust_factor * (-1 if state.velocity.y > 0 else 1)
            thrust_force += adjust_thrust_force
            self.is_done = True
        # hover point is above -> add new command to do full thrust to reach hover point
        elif dist > 0:
            # if moving opposite, first reverse direction
            if state.velocity.y < 0:
                thrust_force = state.max_thrust
            else:
                # keep thrusting till we can reach destination with 0 velocity
                thrust_till_position = (2 * state.gravity * dist - state.velocity.y**2) * (state.mass / (2 * state.max_thrust))
                if thrust_till_position > 0:
                    thrust_force = state.max_thrust
        # hover point is below
        elif dist < 0:
            # if moving opposite, first reverse direction using gravity
            if state.velocity.y > 0:
                thrust_force = 0
            else:
                # if velocity is fast enough to just stop at location at full thrust (in reverse)
                if abs(state.velocity.y) > math.sqrt(2 * (state.max_thrust / state.mass - state.gravity) * -dist):
                    thrust_force = state.max_thrust
        return thrust_force, nozzle_angle

class LandCommand(GuidanceCommand):
    def __init__(self, pad: LaunchPad, rocket_height: float, hover_height: float = 10, descent_velocity: float = 3) -> None:
        super().__init__()
        self.land_y = pad.position.y + rocket_height
        self.target_y = pad.position.y + rocket_height + hover_height # direct hover descent till this stage
        self.rocket_height = rocket_height
        self.descent_velocity = descent_velocity
    
    def draw(self, pyg: PygameBackend) -> None:
        pyg.color((0, 200, 0))
        pyg.circle((0, self.target_y), 2)
        pyg.color((200, 200, 0))
        pyg.circle((0, self.land_y - self.rocket_height), 2)

    def run(self, state: RocketState) -> Tuple[float, float]:
        thrust_force = 0
        nozzle_angle = 0
        dist = self.target_y - state.position.y
        if dist < 0: # if hover point is below, first hover to location with final speed as descent_velocity
            # if velocity is downwards and it is enough to reach the location with final velocity as descent_velocity (when we do max thrust)
            if state.velocity.y <= 0 and abs(state.velocity.y) > math.sqrt(self.descent_velocity**2 + 2 * (state.max_thrust / state.mass - state.gravity) * -dist):
                thrust_force = state.max_thrust
            # thrust_force, nozzle_angle = HoverAtCommand(Vector2D(0, self.target_y)).run(state)
        else:
            # if too close to ground
            if abs(self.land_y - state.position.y) < self.DISTANCE_THRESHOLD:
                self.is_done = True
            # slowly descent towards ground
            else:
                thrust_force = state.mass * state.gravity
                adjust_factor = 0.1
                # slight adjustments (slightly reduce thrust if velocity is too less, otherwise slightly increase it)
                adjust_thrust_force = thrust_force * adjust_factor * (-1 if abs(state.velocity.y) < self.descent_velocity else 1)
                thrust_force += adjust_thrust_force
        return thrust_force, nozzle_angle

class SetPitchCommand(GuidanceCommand):
    def __init__(self, target_angle: float = 0) -> None:
        super().__init__()
        self.target_angle = target_angle
        self.target_direction = Vector2D.up(1).rotate(self.target_angle, origin=Vector2D.origin())
        self.state = None
    
    def draw(self, pyg: PygameBackend) -> None:
        if self.state != None:
            pyg.color((0, 200, 0))
            dir_vec = Vector2D.up(30).rotate(self.target_angle, origin=Vector2D.origin()) + self.state.position
            pyg.line(self.state.position.tuple(), dir_vec.tuple(), width=1.5)
            pyg.color((200, 0, 0))
            dir_vec = Vector2D.up(30).rotate(self.state.angle, origin=Vector2D.origin()) + self.state.position
            pyg.line(self.state.position.tuple(), dir_vec.tuple(), width=1.5)
    
    def run(self, state: RocketState, min_thrust_factor: float = 0.5) -> Tuple[float, float]:
        self.state = state # save state for drawing
        nozzle_angle = 0
        thrust_force = 0
        # find angle between current direction and target direction
        rocket_direction = Vector2D.up(1).rotate(state.angle, origin=Vector2D.origin())
        angle_diff = rocket_direction.angle(self.target_direction)
        # if reached target angle with zero angular velocity
        if abs(angle_diff) < self.ANGLE_THRESHOLD and abs(state.angular_velocity) < self.VELOCITY_THRESHOLD:
            self.is_done = True
        # rotate and stop and target angle
        else:
            # simulated and found constants
            nozzle_constant = math.pi / 4
            velocity_constant = 1.5
            thrust_constant = 0.5
            # calculate nozzle_angle and thrust_force
            nozzle_angle = nozzle_constant * (velocity_constant * state.angular_velocity - angle_diff) # if angular velocity -> move nozzle in that direction | if angle difference -> move nozzle in opposite direction
            thrust_force = state.max_thrust * (state.angular_velocity * thrust_constant + min_thrust_factor)
        return thrust_force, nozzle_angle

class StabilizeCommand(GuidanceCommand):
    # use set pitch to align against velocity vector
    # use enough thrust to get that velocity to zero
    # if pitch is nearly zero, just do normal hover
    def __init__(self) -> None:
        super().__init__()
        self.sub_command = None
    
    def draw(self, pyg: PygameBackend) -> None:
        if self.sub_command != None:
            self.sub_command.draw(pyg=pyg)
    
    def run(self, state: RocketState) -> Tuple[float, float]:
        thrust_force = 0
        nozzle_angle = 0
        # if angle, velocity and angular velocity are zero => then rocket is stabilized
        if abs(state.angle) < self.ANGLE_THRESHOLD and abs(state.angular_velocity) < self.VELOCITY_THRESHOLD:
            if abs(state.velocity.y) > self.VELOCITY_THRESHOLD:
                thrust_force = state.max_thrust
            else:
                thrust_force = state.mass * state.gravity
                self.is_done = True
            self.sub_command = None
        else:
            velocity_opp_angle = 0.1 * Vector2D.up().angle(-state.velocity) # math.pi - velocity_angle
            self.sub_command = SetPitchCommand(velocity_opp_angle)
            thrust_force, nozzle_angle = self.sub_command.run(state)
        return thrust_force, nozzle_angle

class GoTowardsCommand(GuidanceCommand):
    # use set pitch along with thrust change to direct rocket to a point
    # calculate dynamically which point to go towards in order to reach the destination (with gravity in mind)
    ...

class RocketGuidance:
    def __init__(self, pad: LaunchPad = None, rocket: Rocket = None) -> None:
        # rocket.position = Vector2D(-10, 800)
        # rocket.velocity = Vector2D(-40, -40)
        # rocket.angular_velocity = math.pi * 0.6
        # list of commands and the duration to hold command after flagged done
        self.commands: List[Tuple[GuidanceCommand, float]] = [
            (HoverAtCommand(Vector2D(0, 200)), 5),
            (LandCommand(pad, rocket.get_height_from_center(), hover_height=5, descent_velocity=2), 10),
            (HoverAtCommand(Vector2D(0, 100)), 5),
            # (SetPitchCommand(math.pi / 4), 3),
            # (StabilizeCommand(), 5),
        ]
        self.command_done_time = -1
        self.current_stage = 0

    def draw(self, pyg: PygameBackend) -> None:
        self.commands[self.current_stage][0].draw(pyg)

    def run(self, rocket: Rocket) -> None:
        command, command_hold_duration = self.commands[self.current_stage]
        # run the command and get the calculated thrust force and nozzle angle
        state = RocketState(rocket) # abstraction for rocket variables (to protect the actual rocket object)
        thrust_force, nozzle_angle = command.run(state) # run the current guidance stage and get the thrust force and nozzle angle for the rocket
        # clip and set thrust for the rocket
        thrust_factor = thrust_force / rocket.max_thrust # thrust_force = thrust_factor * max_thrust
        rocket.thrust_factor = clip(thrust_factor, 0, 1)
        # clip and set nozzle angle for the rocket
        nozzle_factor = nozzle_angle / rocket.max_nozzle_angle # nozzle_angle = nozzle_factor * max_nozzle_angle
        rocket.nozzle_factor = clip(nozzle_factor, -1, 1)

        # check if command has reached end state (is done)
        if command.is_done:
            # if done is flagged for the first time, we start the clock
            if self.command_done_time == -1:
                self.command_done_time = time.time()
            # if flagged for more than hold duration, update stage if possible
            if time.time() - self.command_done_time > command_hold_duration:
                self._next_stage()
    
    def _next_stage(self):
        if self.current_stage < len(self.commands) - 1:
            self.current_stage += 1 # go to next stage
            self.command_done_time = -1 # reset done time flag

class App(Avour):
    SCREEN_SIZE = (1200, 800)
    SCREEN_BACKGROUND = (10, 10, 10)

    def __init__(self, guidance_enabled: bool = True) -> None:
        super().__init__(window_name='rocket sim', font_name='Arial', font_size=18)
        self.scale(1)
        self.translate((self.SCREEN_SIZE[0] // 2, self.SCREEN_SIZE[1] // 2))
        self.invert_y_axis(True)
        self.rocket = Rocket()
        self.pad = LaunchPad((0, -300), screen_width=self.SCREEN_SIZE[0]) # -140 (for scale=1)
        self.pad.set_rocket_on_ground(self.rocket)
        self.guidance = RocketGuidance(pad=self.pad, rocket=self.rocket)
        self.guidance_enabled = guidance_enabled
        self.active_keys = set()

    def on_keydown(self, key: int) -> None:
        if key == pygame_key_type.K_ESCAPE:
            self.STOP_RUN_LOOP = True
        elif key == pygame_key_type.K_q:
            self.STOP_RUN_LOOP = True
        elif key == pygame_key_type.K_w:
            self.active_keys.add('w')
        elif key == pygame_key_type.K_s:
            self.active_keys.add('s')
        elif key == pygame_key_type.K_a:
            self.active_keys.add('a')
        elif key == pygame_key_type.K_d:
            self.active_keys.add('d')
        elif key == pygame_key_type.K_g:
            self.guidance_enabled = not self.guidance_enabled
        elif key == pygame_key_type.K_n:
            self.guidance._next_stage()
    
    def on_keyup(self, key: int) -> None:
        if key == pygame_key_type.K_w:
            self.active_keys.remove('w')
        elif key == pygame_key_type.K_s:
            self.active_keys.remove('s')
        elif key == pygame_key_type.K_a:
            self.active_keys.remove('a')
        elif key == pygame_key_type.K_d:
            self.active_keys.remove('d')

    def rocket_physics_loop(self, render_dt: float, physics_dt: float = 0.001):
        physics_update_cycles = int(render_dt / physics_dt)
        for _ in range(physics_update_cycles):
            # rocket autopilot guidance update (only if enabled)
            if self.guidance_enabled:
                self.guidance.run(self.rocket)
            # rocket physics update
            self.rocket.update(dt=physics_dt)
            # ground physics
            self.pad.check_and_set_rocket_on_ground(self.rocket)

    def frame(self) -> None:
        # frame init
        self.background()

        # rocket input (only if guidance is not enabled)
        if not self.guidance_enabled:
            self.rocket.set_input(forward=('w' in self.active_keys), backward=('s' in self.active_keys), nozzle_left=('d' in self.active_keys), nozzle_right=('a' in self.active_keys))
        # rocket physics loop (separate from render loop)
        self.rocket_physics_loop(render_dt=self.delta_time())

        # drawing objects
        self.rocket.draw(self)
        self.pad.draw(self)
        if self.guidance_enabled:
            self.guidance.draw(self)
        
        # drawing hardware metrics
        self.show_performance_metrics()

        # other components
        self.rocket.draw_guides(self)
        self.push()
        self.scale(1)
        self.invert_y_axis(False)
        self.rocket.draw_HUD(self)
        self.rocket.draw_telemetry_as_text(self)
        self.rocket.flight_data.draw(self)
        self.pop()

app = App(guidance_enabled=True)
app.run()
