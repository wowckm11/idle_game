import pygame

class Content:
    """
    Represents an item or upgrade available in the shop.
    """
    def __init__(self, name: str, image: pygame.Surface, cost: int):
        self.name = name
        self.image = image
        self.cost = cost

def load_images():
    global image_dict
    image_dict = {}
    try:
        reactor_slot_background = pygame.image.load('reactor_slot_background.png')
        image_dict["reactor_slot_background"] = reactor_slot_background
    except pygame.error as message:
        print("nie udało się wczytać obrazka")

class Box:
    """
    A single box cell in a grid. Stores its position, size, occupancy, and a dict of multipliers.
    """
    def __init__(self, row: int, col: int, size: int, origin: tuple = (0, 0), multipliers: dict = None):
        # Grid coordinates
        self.row = row
        self.col = col
        # Pixel size of the box
        self.size = size
        x = origin[0] + col * size
        y = origin[1] + row * size
        # Rectangle for rendering and collision
        self.rect = pygame.Rect(x, y, size, size)
        # Occupied flag and stored object
        self.occupied = False
        self.content = None
        # Multipliers affecting this box (e.g., production, speed, etc.)
        self.multipliers = multipliers or {}

    def draw(self, surface: pygame.Surface):
        """
        Draw the box outline and optionally its content on the given surface.
        """
        
        # Outline color: red if occupied, gray if empty
        outline_color = (200, 50, 50) if self.occupied else (200, 200, 200)
        
        surface.blit(image_dict["reactor_slot_background"],self.rect)

        # If there's content, let it draw itself
        if self.content and hasattr(self.content, 'draw'):
            # Center content in the box
            content_rect = self.content.image.get_rect(center=self.rect.center)
            surface.blit(self.content.image, content_rect)

    def is_hovered(self, mouse_pos: tuple) -> bool:
        """
        Check if the mouse position is over this box.
        """
        return self.rect.collidepoint(mouse_pos)

    def place(self, obj) -> bool:
        """
        Place an object into this box if it's empty. Returns True if placed.
        """
        if not self.occupied:
            self.occupied = True
            self.content = obj
            return True
        return False

    def remove(self):
        """
        Clear the box and remove its content.
        """
        self.occupied = False
        self.content = None

class ShopBox:
    """
    A box in the shop UI. Has a cost, a content, and an active (purchased) state.
    Draws with a colored outline based on its active state.
    """
    def __init__(self, position: tuple, size: int, cost: int, content: Content):
        self.position = position
        self.size = size
        self.rect = pygame.Rect(position[0], position[1], size, size)
        self.cost = cost
        self.content = content
        self.active = False
        # Initialize outline color
        self.outline_color = (200, 200, 200)
        self.font = pygame.font.Font(None, 24)

    def draw(self, surface: pygame.Surface):
        # Draw rectangle outline with current color
        pygame.draw.rect(surface, self.outline_color, self.rect, 2)
        # Draw content image centered
        img_rect = self.content.image.get_rect(center=self.rect.center)
        surface.blit(self.content.image, img_rect)
        # Draw cost below box
        cost_surf = self.font.render(str(self.cost), True, (255, 255, 255))
        cost_rect = cost_surf.get_rect(midtop=(self.rect.centerx, self.rect.bottom + 4))
        surface.blit(cost_surf, cost_rect)

    def is_hovered(self, mouse_pos: tuple) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def toggle(self) -> bool:
        """
        Toggle the active state of this shop box. Updates outline color.
        Returns the new state.
        """
        self.active = not self.active
        # Update outline color based on new state
        if self.active:
            self.outline_color = (50, 200, 50)
        else:
            self.outline_color = (200, 200, 200)
        return self.active


class Shop:
    """
    A simple shop UI composed of a fixed row of ShopBox items.
    """
    def __init__(self, origin: tuple, box_size: int, contents: list, spacing: int=10):
        # costs: list of 4 int costs, contents: list of 4 Content instances
        self.box_size = box_size
        self.origin = origin
        self.items = []
        for i in range(len(contents)):
            x = origin[0] + i * (box_size + spacing)
            y = origin[1]
            self.items.append(ShopBox((x, y), box_size, contents[i].cost, contents[i]))

    def draw(self, surface: pygame.Surface):
        for item in self.items:
            item.draw(surface)

    def handle_click(self, mouse_pos: tuple, surface) -> bool:
        for item in self.items:
            if item.is_hovered(mouse_pos):
                item.toggle()
                return True
        return False

class Grid:
    """
    A grid of Box cells arranged in rows and columns.
    """
    def __init__(self, rows: int, cols: int, box_size: int, origin: tuple = (0, 0)):
        self.rows = rows
        self.cols = cols
        self.box_size = box_size
        self.origin = origin
        # Create a 2D list of Box instances
        self.cells = [
            [Box(r, c, box_size) for c in range(cols)]
            for r in range(rows)
        ]

    def draw(self, surface: pygame.Surface):
        """
        Draw all boxes in the grid.
        """
        for row in self.cells:
            for box in row:
                box.draw(surface)

    def handle_click(self, mouse_pos: tuple, placer_fn):
        """
        On click, find the clicked box and attempt to place an object via placer_fn.
        placer_fn should be a function that returns an object with a .image attribute.
        """
        for row in self.cells:
            for box in row:
                if box.is_hovered(mouse_pos):
                    if box.place(placer_fn()):
                        return True
        return False


pygame.init()

load_images()

screen = pygame.display.set_mode((800, 600))
grid = Grid(rows=10, cols=10, box_size=50, origin=(500,500))

power_img = pygame.Surface((32, 32)); power_img.fill((255, 215, 0))
speed_img = pygame.Surface((32, 32)); speed_img.fill((0, 200, 255))
contents = [Content("Power", power_img, 100), Content("Speed", speed_img, 200), Content("Reach", power_img, 500), Content("Value", speed_img, 1000)]
costs = [100, 200, 300, 400]
shop = Shop(origin=(550, 50), box_size=50, contents=contents)

def create_dummy_sprite():
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((40, 40))
    sprite.image.fill((0, 255, 0))
    return sprite

running = True
while running:
    
    screen.fill((30, 30, 30))
    grid.draw(screen)
    shop.draw(screen)
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            grid.handle_click(event.pos, create_dummy_sprite)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            shop.handle_click(event.pos)

pygame.quit()
