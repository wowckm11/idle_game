import pygame

# --- Content Class ---
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
        uranium_rod = pygame.image.load('uranium_rod.png')
        image_dict["uranium_rod"] = uranium_rod
    except pygame.error:
        print("Failed to load reactor_slot_background.png")


# --- Box and Grid Classes ---
class Box:
    """
    A single box cell in a grid.
    """
    def __init__(self, row: int, col: int, size: int, origin: tuple = (0, 0), multipliers: dict = None):
        self.row = row
        self.col = col
        self.size = size
        x = origin[0] + col * size
        y = origin[1] + row * size
        self.rect = pygame.Rect(x, y, size, size)
        self.occupied = False
        self.content = None
        self.multipliers = multipliers or {}

    def draw(self, surface: pygame.Surface):
        surface.blit(image_dict.get("reactor_slot_background"), self.rect)
        if self.content:
            content_rect = self.content.image.get_rect(center=self.rect.center)
            surface.blit(self.content.image, content_rect)

    def is_hovered(self, mouse_pos: tuple) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def place(self, obj) -> bool:
        if not self.occupied:
            self.occupied = True
            self.content = obj
            return True
        return False

    def remove(self):
        self.occupied = False
        self.content = None


class Grid:
    """
    A grid of Box cells.
    """
    def __init__(self, rows: int, cols: int, box_size: int, origin: tuple = (0, 0)):
        self.box_size = box_size
        self.cells = [
            [Box(r, c, box_size, origin) for c in range(cols)]
            for r in range(rows)
        ]

    def draw(self, surface: pygame.Surface):
        for row in self.cells:
            for box in row:
                box.draw(surface)

    def handle_click(self, mouse_pos: tuple, placer_fn) -> bool:
        for row in self.cells:
            for box in row:
                if box.is_hovered(mouse_pos) and box.place(placer_fn):
                    return True
        return False


# --- Shop Classes ---
class ShopBox:
    """
    A toggleable shop cell with cost and content.
    """
    def __init__(self, position: tuple, size: int, content: Content):
        self.rect = pygame.Rect(position[0], position[1], size, size)
        self.content = content
        self.active = False
        self.outline_color = (200, 200, 200)
        self.font = pygame.font.Font(None, 24)

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.outline_color, self.rect, 2)
        img_rect = self.content.image.get_rect(center=self.rect.center)
        surface.blit(self.content.image, img_rect)
        cost_surf = self.font.render(str(self.content.cost), True, (255, 255, 255))
        cost_rect = cost_surf.get_rect(midtop=(self.rect.centerx, self.rect.bottom + 4))
        surface.blit(cost_surf, cost_rect)

    def is_hovered(self, mouse_pos: tuple) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.outline_color = (50, 200, 50) if self.active else (200, 200, 200)


class Shop:
    """
    A horizontal row of ShopBox items where only one can be active at a time.
    """
    def __init__(self, origin: tuple, box_size: int, contents: list, spacing: int = 10):
        self.items = []
        for i, content in enumerate(contents):
            x = origin[0] + i * (box_size + spacing)
            y = origin[1]
            self.items.append(ShopBox((x, y), box_size, content))

    def draw(self, surface: pygame.Surface):
        for item in self.items:
            item.draw(surface)

    def handle_click(self, mouse_pos: tuple) -> bool:
        clicked = False
        for item in self.items:
            if item.is_hovered(mouse_pos):
                item.set_active(True)
                clicked = True
            else:
                item.set_active(False)
        return clicked

    def get_active_content(self):
        """
        Returns the Content of the currently active ShopBox, or None if none active.
        """
        for item in self.items:
            if item.active:
                return item.content
        return None


# --- Main Loop ---
pygame.init()
load_images()
screen = pygame.display.set_mode((800, 600))

grid = Grid(rows=10, cols=10, box_size=50, origin=(300, 50))
dummy_img1 = pygame.Surface((32, 32)); dummy_img1.fill((255, 215, 0))
dummy_img2 = pygame.Surface((32, 32)); dummy_img2.fill((0, 200, 255))
contents = [Content("Power", image_dict["uranium_rod"], 100), Content("Speed", dummy_img2, 200)]
shop = Shop(origin=(20, 50), box_size=50, contents=contents)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Toggle shop or place in grid
            active = shop.get_active_content()
            if active:
                # Place the currently selected shop Content into the grid
                grid.handle_click(event.pos, active)
            if not shop.handle_click(event.pos):
                pass

    screen.fill((30, 30, 30))
    grid.draw(screen)
    shop.draw(screen)
    pygame.display.flip()

pygame.quit()
