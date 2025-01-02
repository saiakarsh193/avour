import time
import random
from typing import List
from avour import Avour, COORD2INT, COORD2FLOAT
from utils.math import clip
from utils.vector import Vector2D
from utils.physics import rect_collision
from utils.draw import SpriteVertexGroup, SpriteShape

class Shooter:
    speed = 10
    dim: COORD2FLOAT = (30, 70) # width, height
    screen_x_threshold = 100

    def __init__(self, screen_size: COORD2INT) -> None:
        self.pos = Vector2D(0, -screen_size[1] / 2 + 150)
        self.screen_size = screen_size

        # svg
        rocket_body = SpriteVertexGroup(
            SpriteShape.rect((0, 0), self.dim[0], self.dim[1]),
            color=(100, 100, 100)
        )
        rocket_fin = SpriteVertexGroup([
            (1, 0),
            (0.5, 1.3),
            (0, 1.3),
            (0, 0)
        ], color=(255, 100, 100))
        rocket_cone = SpriteVertexGroup([
            (-1, 0),
            (1, 0),
            (0, 2)
        ], color=(100, 100, 100))
        rocket_cone2 = SpriteVertexGroup([
            (-1, 0),
            (1, 0),
            (0, 3)
        ], color=(100, 100, 100))
        rocket_exhaust = SpriteVertexGroup(
            SpriteShape.rect((0, 0), 10, 30),
            color=(255, 136, 51)
        )
        rocket_exhaust2 = SpriteVertexGroup(
            SpriteShape.rect((0, 0), 10, 40),
            color=(255, 73, 28)
        )

        self.svg = SpriteVertexGroup() # empty group to hold other groups
        self.svg.add_group(rocket_body, origin=Vector2D(-self.dim[0] / 2, 0), scale=1)
        self.svg.add_group(rocket_fin, origin=Vector2D(self.dim[0] / 2, -self.dim[1]), scale=15)
        self.svg.add_group(rocket_fin.flip_on_x(), origin=Vector2D(-self.dim[0] / 2, -self.dim[1]), scale=15)
        self.svg.add_group(rocket_exhaust, origin=Vector2D(-5, -self.dim[1]), scale=1)
        self.svg.add_group(rocket_cone, origin=Vector2D(0, 0), scale=15)
        self.svg.add_group(rocket_cone2, origin=Vector2D(0, -self.dim[1] -10), scale=10)

    def move(self, left: int = 0, right: int = 0) -> None:
        if left > 0:
            left = clip(left / 20, 0, 1)
            self.pos.x = self.pos.x - self.speed * left
        if right > 0:
            right = clip(right / 20, 0, 1)
            self.pos.x = self.pos.x + self.speed * right
        self.pos.x = clip(self.pos.x, -self.screen_size[0] / 2 + self.screen_x_threshold, self.screen_size[0] / 2 - self.screen_x_threshold - self.dim[0])

    def hit_obstacle(self, obstacle: 'Obstacle') -> bool:
        rocket_top = self.pos.tuple()
        rocket_bot = (rocket_top[0] + self.dim[0], rocket_top[1] + self.dim[1])
        obstacle_top = obstacle.pos.tuple()
        obstacle_bot = (obstacle_top[0] + obstacle.dim[0], obstacle_top[1] + obstacle.dim[1])
        return rect_collision(rocket_top, rocket_bot, obstacle_top, obstacle_bot)

    def draw(self, avour: Avour) -> None:
        for shape in self.svg.shapes(origin=self.pos, scale=1):
            avour.color(shape.color)
            avour.polygon(shape.vertices)

class Bullet:
    speed = 25
    dim: COORD2FLOAT = (5, 10) # width, height

    def __init__(self, pos: Vector2D) -> None:
        self.pos = pos

    def update(self) -> None:
        self.pos.y += self.speed

    def oos(self, screen_size: COORD2INT) -> bool:
        if abs(self.pos.y) > screen_size[1] / 2:
            return True
        return False

    def draw(self, avour: Avour) -> None:
        avour.fill(True)
        avour.color((255, 100, 100))
        avour.rect(self.pos.tuple(), self.dim[0], self.dim[1])
    
class PowerUp:
    speed = 4
    dim: COORD2FLOAT = (25, 25) # width, height
    screen_x_threshold = 100
    tags = ['bullet_fast', 'bullet_multiple']

    def __init__(self, pos: Vector2D, tag: str) -> None:
        self.pos = pos
        self.tag = tag

    def update(self) -> None:
        self.pos.y -= self.speed

    def oos(self, screen_size: COORD2INT) -> bool:
        if abs(self.pos.y) > screen_size[1] / 2:
            return True
        return False

    def draw(self, avour: Avour) -> None:
        avour.fill(True)
        if self.tag == 'bullet_fast':
            avour.color((106, 21, 171))
        else:
            avour.color((151, 237, 45))
        avour.rect(self.pos.tuple(), self.dim[0], self.dim[1])

    @staticmethod
    def spawn(screen_size: COORD2INT) -> 'PowerUp':
        return PowerUp(Vector2D((random.random() * 2 - 1) * (screen_size[0] / 2 - PowerUp.screen_x_threshold), screen_size[1] / 2), random.choice(PowerUp.tags))

class Obstacle:
    speed = 50
    dim: COORD2FLOAT = (70, 40) # width, height
    separation = 40

    def __init__(self, pos: Vector2D) -> None:
        self.pos = pos

    def update(self) -> None:
        self.pos.y -= self.speed

    def oos(self, screen_size: COORD2INT) -> bool:
        if abs(self.pos.y) > screen_size[1] / 2:
            return True
        return False
    
    def hit_bullet(self, bullet: Bullet) -> bool:
        bullet_top = bullet.pos.tuple()
        bullet_bot = (bullet_top[0] + bullet.dim[0], bullet_top[1] + bullet.dim[1])
        obstacle_top = self.pos.tuple()
        obstacle_bot = (obstacle_top[0] + self.dim[0], obstacle_top[1] + self.dim[1])
        return rect_collision(bullet_top, bullet_bot, obstacle_top, obstacle_bot)

    def draw(self, avour: Avour) -> None:
        avour.fill(True)
        avour.color((100, 100, 255))
        avour.rect(self.pos.tuple(), self.dim[0], self.dim[1])

class Manager:
    def __init__(self, shooter: Shooter, screen_size: COORD2INT) -> None:
        self.shooter = shooter
        self.screen_size = screen_size

        # bullet variables
        self.bullets: List[Bullet] = []
        self.bullet_shot = 1
        self.last_bullet_time = time.time()
        self.bullet_interval = 0.3
        self.bullet_update_time = time.time()
        self.bullet_update_interval = 0.02

        # obstacle variables
        self.obstacles: List[Obstacle] = []
        self.obstacles_left_to_spawn = 0
        self.max_obstacles_in_grid = (self.screen_size[0] - Obstacle.separation) // (Obstacle.dim[0] + Obstacle.separation)
        self.max_obstacles_per_update = 3
        self.obstacle_update_time = time.time()
        self.obstacle_update_interval = 1

        # power up variables
        self.power_ups: List[PowerUp] = []
        self.last_power_up_time = time.time()
        self.last_power_up_interval = 10
        self.power_up_update_time = time.time()
        self.power_up_update_interval = 1.2
        self.power_up_tag = ''
        self.power_up_start_time = 0
        self.power_up_start_interval = 4

        # setup the game and waves
        self.max_lives = 5
        self.lives = self.max_lives
        self.max_levels = 4
        self.level = -1
        self.level_start_time = 0
        self.level_start_interval = 4

    def set_level(self, level: int) -> None:
        self.level = level
        self.level_start_time = time.time()
        if level == 0:
            self.obstacle_update_interval = 0.8
            self.obstacles_left_to_spawn = 10
        elif level == 1:
            self.obstacle_update_interval = 0.7
            self.obstacles_left_to_spawn = 12
        elif level == 2:
            self.obstacle_update_interval = 0.6
            self.obstacles_left_to_spawn = 14
        elif level == 3:
            self.obstacle_update_interval = 0.5
            self.obstacles_left_to_spawn = 16
        elif level == 4:
            self.obstacle_update_interval = 0.4
            self.obstacles_left_to_spawn = 20

    def setup_wave(self) -> None:
        if self.obstacles_left_to_spawn <= 0:
            return
        screen_y_threshold = 100
        obstacles_to_spawn = random.randint(0, self.max_obstacles_per_update)
        obstacles_to_spawn = min(obstacles_to_spawn, self.obstacles_left_to_spawn)
        obstacle_indices = random.sample(list(range(self.max_obstacles_in_grid)), k=obstacles_to_spawn)
        for ind in obstacle_indices:
            self.obstacles.append(
                    Obstacle(
                        Vector2D(
                            Obstacle.separation + (Obstacle.separation + Obstacle.dim[0]) * ind - self.screen_size[0] / 2,
                            self.screen_size[1] / 2 - screen_y_threshold
                        )
                    )
                )
            self.obstacles_left_to_spawn -= 1

    def shoot_bullet(self, space: bool = False) -> None:
        if not space:
            return
        if time.time() - self.last_bullet_time > self.bullet_interval:
            self.bullets.append(Bullet(self.shooter.pos + Vector2D.left(Bullet.dim[0] / 2)))
            if self.bullet_shot == 3:
                self.bullets.append(Bullet(self.shooter.pos + Vector2D.left(Bullet.dim[0] / 2) + Vector2D.left(Bullet.dim[0] * 2.5)))
                self.bullets.append(Bullet(self.shooter.pos + Vector2D.left(Bullet.dim[0] / 2) + Vector2D.right(Bullet.dim[0] * 2.5)))
            self.last_bullet_time = time.time()

    def handle_oos(self) -> int:
        remove_bullets = []
        for bullet in self.bullets:
            if bullet.oos(self.screen_size):
                remove_bullets.append(bullet)
        for bullet in remove_bullets:
            self.bullets.remove(bullet)
        remove_obstacles = []
        for obstacle in self.obstacles:
            if obstacle.oos(self.screen_size):
                remove_obstacles.append(obstacle)
        for obstacle in remove_obstacles:
            self.obstacles.remove(obstacle)
        remove_power_ups = []
        for power_up in self.power_ups:
            if power_up.oos(self.screen_size):
                remove_power_ups.append(power_up)
        for power_up in remove_power_ups:
            self.power_ups.remove(power_up)
        return len(remove_obstacles)

    def handle_collisions(self) -> None:
        remove_bullets = []
        remove_obstacles = []
        for bullet in self.bullets:
            for obstacle in self.obstacles:
                if obstacle.hit_bullet(bullet):
                    remove_bullets.append(bullet)
                    if not obstacle in remove_obstacles:
                        remove_obstacles.append(obstacle)

        for bullet in remove_bullets:
            self.bullets.remove(bullet)
        for obstacle in remove_obstacles:
            self.obstacles.remove(obstacle)

    def update(self) -> int:
        # update bullets every period
        if time.time() - self.bullet_update_time > self.bullet_update_interval:
            for bullet in self.bullets:
                bullet.update()
            self.bullet_update_time = time.time()

        # update power ups every period
        if time.time() - self.power_up_update_time - self.power_up_update_interval:
            for power_up in self.power_ups:
                power_up.update()
            self.power_up_update_time = time.time()

        # add new power ups every period
        if time.time() - self.last_power_up_time > self.last_power_up_interval:
            self.power_ups.append(PowerUp.spawn(self.screen_size))
            self.last_power_up_time = time.time()

        # handling power up effect
        if time.time() - self.power_up_start_time < self.power_up_start_interval:
            if self.power_up_tag == 'bullet_fast':
                self.bullet_interval = 0.1
            elif self.power_up_tag == 'bullet_multiple':
                self.bullet_shot = 3
        else:
            # default values for power up modified variables
            self.bullet_shot = 1
            self.bullet_interval = 0.3
        
        # out of screen
        obstacles_oos = self.handle_oos()
        # remove one life for each obstacle missed
        self.lives -= obstacles_oos
        # obstacle - bullet collision
        self.handle_collisions()
        
        # obstacle - shooter collision: remove life if collision with obstacle
        for obstacle in self.obstacles:
            if self.shooter.hit_obstacle(obstacle):
                self.obstacles.remove(obstacle)
                self.lives -= 1
                break

        # obstacle - power_up collision: start timer if collision
        for power_up in self.power_ups:
            if self.shooter.hit_obstacle(power_up):
                self.power_ups.remove(power_up)
                self.power_up_tag = power_up.tag
                self.power_up_start_time = time.time()
                break

        #########################
        # stop updating obstacles during level start interval
        if time.time() - self.level_start_time < self.level_start_interval:
            return 0

        # update obstacles every period
        # add new obstacles as they move
        if time.time() - self.obstacle_update_time > self.obstacle_update_interval:
            for obstacle in self.obstacles:
                obstacle.update()
            self.setup_wave()
            self.obstacle_update_time = time.time()

        # update the level
        # when all obstacles were spawned and destroyed
        if self.obstacles_left_to_spawn == 0 and len(self.obstacles) == 0:
            # if reached last level, stop with status 1
            if self.level >= self.max_levels:
                return 1
            self.set_level(self.level + 1)
        
        # if normal, return with status 0
        if self.lives > 0:
            return 0
        # if lives are over, stop with status -1
        else:
            return -1

    def draw(self, avour: Avour) -> None:
        # drawing other objects
        avour.fill(True)
        self.shooter.draw(avour)
        for bullet in self.bullets:
            bullet.draw(avour)
        for obstacle in self.obstacles:
            obstacle.draw(avour)
        for power_up in self.power_ups:
            power_up.draw(avour)

        # if level start interval, show the wave info and return
        if time.time() - self.level_start_time < self.level_start_interval:
            avour.color(200)
            avour.text(f'WAVE {self.level + 1}', (0, 0), anchor_x='center', bold=True, font_size=40)
            return

        # drawing remaining lives
        for i in range(self.lives):
            avour.color((255, 65, 43))
            avour.fill(True)
            avour.circle((-self.screen_size[0] / 2 + 15 + 30 * i, self.screen_size[1] / 2 - 15), 10)
        # drawing all lives (empty border)
        for i in range(self.max_lives):
            avour.fill(False)
            avour.color(255)
            avour.circle((-self.screen_size[0] / 2 + 15 + 30 * i, self.screen_size[1] / 2 - 15), 10)

        avour.color(255)
        avour.text(f'wave {self.level + 1}', (self.screen_size[0] / 2, self.screen_size[1] / 2), anchor_x='right', anchor_y='top', font_size=15)

class App(Avour):
    def __init__(self) -> None:
        super().__init__(screen_title='shooter', show_fps=True)
        self.set_frame_rate(80)
        self.set_physics_rate(100)
        screen_size = self.get_screen_size()
        self.translate((screen_size[0] / 2, screen_size[1] / 2))
        self.shooter = Shooter(screen_size)
        self.manager = Manager(self.shooter, screen_size)
        self.game_over = 0

    def on_keydown(self, key: str) -> None:
        if key == 'ESCAPE' or key == 'Q':
            self.exit()

    def draw(self) -> None:
        self.background(10)
        if self.game_over == -1:
            self.color(200)
            self.text('YOU DIED', (0, 0), anchor_x='center', bold=True, font_size=40)
        elif self.game_over == 1:
            self.color(200)
            self.text('YOU WON', (0, 0), anchor_x='center', bold=True, font_size=40)
        else:
            self.manager.draw(self)

    def loop(self, dt: float) -> None:
        if self.game_over != 0:
            return
        self.shooter.move(
            left=self.keys_active.get('A', 0) + self.keys_active.get('LEFT', 0),
            right=self.keys_active.get('D', 0) + self.keys_active.get('RIGHT', 0),
        )
        self.manager.shoot_bullet(space=('SPACE' in self.keys_active))
        # game_over
        # 0: normal / continue the loop
        # 1: max level reached
        # -1: all lives over
        self.game_over = self.manager.update()

app = App()
app.run()
