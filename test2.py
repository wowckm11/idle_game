import pygame
import datetime
import csv
import os

# --- Content Class ---
class Content:
    """
    Represents an item or upgrade available in the shop.
    """
    def __init__(self, name: str, image: pygame.Surface, cost: int, timeout: int, income: float):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout  # seconds
        self.creation = datetime.datetime.now()
        self.income = income

    def clone(self):
        """
        Create a fresh copy of this content with a new creation timestamp.
        """
        return Content(
            name=self.name,
            image=self.image,
            cost=self.cost,
            timeout=self.timeout,
            income=self.income
        )


def compile_image_list():
    image_list = []
    for item in os.listdir('misc'):
        image_list.append((f'misc/{item}', item[:-4]))
    with open('shop_objects.csv', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_list.append((f'assets/{row["image"]}.png', row['name']))
    return image_list


def load_images():
    global image_dict
    image_dict = {}
    for path, key in compile_image_list():
        try:
            image_dict[key] = pygame.image.load(path)
        except pygame.error:
            print(f"Failed to load {path}")

# --- Box and Grid Classes ---
class Box:
    """
    A single box cell in a grid, with expiration progress bar.
    """
    def __init__(self, row: int, col: int, size: int, origin: tuple = (0, 0)):
        self.row = row
        self.col = col
        self.size = size
        x = origin[0] + col * size
        y = origin[1] + row * size
        self.rect = pygame.Rect(x, y, size, size)
        self.occupied = False
        self.content = None

    def draw(self, surface: pygame.Surface):
        surface.blit(image_dict.get("reactor_slot_background"), self.rect)
        if self.content:
            # Draw content image
            content_rect = self.content.image.get_rect(center=self.rect.center)
            surface.blit(self.content.image, content_rect)
            # Draw timeout progress bar
            now = datetime.datetime.now()
            elapsed = (now - self.content.creation).total_seconds()
            remaining = max(0, self.content.timeout - elapsed)
            ratio = remaining / self.content.timeout if self.content.timeout > 0 else 0
            bar_width = int(self.size * ratio)
            bar_height = 5
            bar_x = self.rect.x
            bar_y = self.rect.y + self.size - bar_height - 2
            pygame.draw.rect(surface, (100, 100, 100), (self.rect.x, bar_y, self.size, bar_height))
            green = (50, 200, 50)
            orange = (255, 165, 0)
            fill_color = (
                int(orange[0] + (green[0] - orange[0]) * ratio),
                int(orange[1] + (green[1] - orange[1]) * ratio),
                int(orange[2] + (green[2] - orange[2]) * ratio)
            )
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, bar_width, bar_height))

    def is_hovered(self, mouse_pos: tuple) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def place(self, content: Content) -> bool:
        if not self.occupied:
            self.occupied = True
            self.content = content.clone()
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

    def place_content(self, mouse_pos: tuple, content: Content) -> bool:
        for row in self.cells:
            for box in row:
                if box.is_hovered(mouse_pos) and box.place(content):
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
    A layout of ShopBox items in rows of 3 per line.
    """
    def __init__(self, origin: tuple, box_size: int, contents: list, spacing: int = 10, items_per_row: int = 3):
        self.items = []
        for idx, content in enumerate(contents):
            row = idx // items_per_row
            col = idx % items_per_row
            x = origin[0] + col * (box_size + spacing)
            y = origin[1] + row * (box_size + spacing)
            box = ShopBox((x, y), box_size, content)
            self.items.append(box)
        # Always have one selected by default
        if self.items:
            self.items[0].set_active(True)

    def draw(self, surface: pygame.Surface):
        for item in self.items:
            item.draw(surface)

    def handle_click(self, mouse_pos: tuple, money: float) -> bool:
        for item in self.items:
            if item.is_hovered(mouse_pos):
                if money >= item.content.cost:
                    for other in self.items:
                        other.set_active(other is item)
                return True
        return False

    def get_active_content(self):
        for item in self.items:
            if item.active:
                return item.content
        return None

# Shop logo rect
shop_logo_rect = pygame.Rect(50, 0, 50, 100)

# --- Main Loop ---
pygame.init()
load_images()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Idle Grid Game')

# Fonts
money_font = pygame.font.Font(None, 36)

# Initialize money
money = 500.0

# Set up timers
INCOME_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(INCOME_EVENT, 100)

# Instantiate
grid = Grid(rows=10, cols=10, box_size=50, origin=(200, 50))
contents = [
    Content("Power", image_dict.get("uranium_rod"), cost=10, timeout=15, income=0.1),
    Content("yellow_rod", image_dict.get("yellow_rod"), cost=20, timeout=20, income=0.2),
    Content("extra1", image_dict.get("yellow_rod"), cost=30, timeout=25, income=0.3),
    Content("extra2", image_dict.get("yellow_rod"), cost=40, timeout=30, income=0.4),
    Content("extra3", image_dict.get("yellow_rod"), cost=50, timeout=35, income=0.5)
]
shop = Shop(origin=(20, 60), box_size=50, contents=contents, spacing=10, items_per_row=3)

running = True
while running:
    now = datetime.datetime.now()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == INCOME_EVENT:
            for row in grid.cells:
                for box in row:
                    if box.content:
                        money += box.content.income
                        elapsed = (now - box.content.creation).total_seconds()
                        if elapsed >= box.content.timeout:
                            box.remove()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if shop.handle_click(pos, money):
                continue
            active = shop.get_active_content()
            if active and money >= active.cost:
                placed = grid.place_content(pos, active)
                if placed:
                    money -= active.cost

    screen.fill((30, 30, 30))
    grid.draw(screen)
    shop.draw(screen)
    screen.blit(image_dict.get('shop_logo'), shop_logo_rect)
    money_surf = money_font.render(f"Money: {round(money)}", True, (255, 255, 0))
    screen.blit(money_surf, (20, 550))
    pygame.display.flip()

pygame.quit()
