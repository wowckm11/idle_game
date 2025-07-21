import pygame

class Box:
    """
    A single box cell in a grid. Stores its position, size, occupancy, and a dict of multipliers.
    """
    def __init__(self, row: int, col: int, size: int, multipliers: dict = None):
        # Grid coordinates
        self.row = row
        self.col = col
        # Pixel size of the box
        self.size = size
        # Rectangle for rendering and collision
        self.rect = pygame.Rect(col * size, row * size, size, size)
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
        pygame.draw.rect(surface, outline_color, self.rect, 2)

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


class Grid:
    """
    A grid of Box cells arranged in rows and columns.
    """
    def __init__(self, rows: int, cols: int, box_size: int):
        self.rows = rows
        self.cols = cols
        self.box_size = box_size
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

# Example usage:
#
# pygame.init()
# screen = pygame.display.set_mode((800, 600))
# grid = Grid(rows=10, cols=10, box_size=50)
#
# def create_dummy_sprite():
#     sprite = pygame.sprite.Sprite()
#     sprite.image = pygame.Surface((40, 40))
#     sprite.image.fill((0, 255, 0))
#     return sprite
#
# running = True
# while running:
#     for event in pygame.event.get():
#         if event.type == pygame.QUIT:
#             running = False
#         elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
#             grid.handle_click(event.pos, create_dummy_sprite)
#
#     screen.fill((30, 30, 30))
#     grid.draw(screen)
#     pygame.display.flip()
#
# pygame.quit()
