import pygame
import datetime
# --- Content Class ---
class Content:
    """
    Represents an item or upgrade available in the shop.
    """
    def __init__(self, name: str, image: pygame.Surface, cost: int, timeout: int, income: int):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout
        self.creation = datetime.datetime.now()
        self.income = income


def load_images():
    global image_dict
    image_dict = {}
    try:
        reactor_slot_background = pygame.image.load('reactor_slot_background.png')
        image_dict["reactor_slot_background"] = reactor_slot_background
        uranium_rod = pygame.image.load('uranium_rod.png')
        image_dict["uranium_rod"] = uranium_rod
        shop_logo = pygame.image.load('shop.png')
        image_dict['shop_logo'] = shop_logo
    except pygame.error:
        print("Failed to load images")


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

    def place(self, content: Content) -> bool:
        if not self.occupied:
            self.occupied = True
            self.content = content
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
        """
        Place the given content into the clicked box, if empty.
        Returns True if placed.
        """
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
    A horizontal row of ShopBox items where only one can be active at a time.
    Click only activates if player has enough money.
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

    def handle_click(self, mouse_pos: tuple, money: int) -> bool:
        """
        Activate the clicked shop box if affordable, deactivate others.
        Returns True if a click was on any box.
        """
        clicked = False
        for item in self.items:
            if item.is_hovered(mouse_pos) and money >= item.content.cost:
                item.set_active(True)
                clicked = True
            else:
                item.set_active(False)
        return clicked

    def get_active_content(self):
        for item in self.items:
            if item.active:
                return item.content
        return None
    
shop_logo_rect = pygame.Rect(50, 0, 50, 100)


# --- Main Loop ---
pygame.init()
load_images()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Idle Grid Game')

# Fonts
money_font = pygame.font.Font(None, 36)

# Initialize money
money = 500

# Set up income timer (every 1 second)
INCOME_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(INCOME_EVENT, 1000)

# Create grid aligned right
grid = Grid(rows=10, cols=10, box_size=50, origin=(200, 50))
# Create shop aligned left
contents = [
    Content("Power", image_dict["uranium_rod"], cost=100, timeout=15, income=1),
    Content("Speed", pygame.Surface((32,32)).convert(), cost=200, timeout=20, income=2)
]
contents[1].image.fill((0,200,255))
shop = Shop(origin=(20, 50), box_size=50, contents=contents)

running = True
while running:
    for event in pygame.event.get():
        
        if event.type == pygame.QUIT:
            running = False
        elif event.type == INCOME_EVENT:
            # Sum income from all placed content
            for row in grid.cells:
                for box in row:
                    if box.content:
                        money += box.content.income
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos=event.pos
            # Toggle shop or place in grid
            active = shop.get_active_content()
            if active and money >= active.cost:
                placed = grid.place_content(pos, active)
                if placed:
                    money -= active.cost
            if not shop.handle_click(pos, money):
                pass

    # Draw everything
    screen.fill((30, 30, 30))
    grid.draw(screen)
    shop.draw(screen)
    screen.blit(image_dict["shop_logo"], shop_logo_rect)

    # Render money counter
    money_surf = money_font.render(f"Money: {money}", True, (255, 255, 0))
    screen.blit(money_surf, (20, 550))

    pygame.display.flip()

pygame.quit()
