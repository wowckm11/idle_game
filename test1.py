import pygame
import csv
import os
import numpy as np

# Pre-calculate heat colors
HEAT_COLORS = [(int(255 * r), int(255 * (1 - r)), 0) for r in np.linspace(0, 1, 256)]

#config
game_speed_actions_per_second=1
game_speed = 1000//game_speed_actions_per_second #number of miliseconds per action 50 => happens 20 times a second

# --- Content Class ---
class Content:
    def __init__(self, name: str, image: pygame.Surface, cost: int,
                 timeout: int, income: float, category: str,
                 heat_generation: float = 0.0, max_heat: float = 5.0,
                 conductivity: float = 0.0):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout/game_speed_actions_per_second
        self.creation = pygame.time.get_ticks()
        self.income = income
        self.category = category
        self.heat = 0.0
        self.heat_generation = heat_generation
        self.max_heat = max_heat
        self.conductivity = conductivity
        self.permanent = (timeout == 0)

    def clone(self):
        return Content(
            name=self.name,
            image=self.image,
            cost=self.cost,
            timeout=self.timeout,
            income=self.income,
            category=self.category,
            heat_generation=self.heat_generation,
            max_heat=self.max_heat,
            conductivity=self.conductivity
        )

def compile_image_list():
    image_list = []
    for item in os.listdir('misc'):
        if item.endswith('.png'):
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

def load_shop_contents():
    contents = []
    with open('shop_objects.csv', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img = image_dict.get(row['image'])
            gen = float(row.get('heat_generation', 0.0))
            mh  = float(row.get('max_heat', 5.0))
            cond = float(row.get('conductivity', 0.0))
            contents.append(Content(
                row['name'], img,
                int(row['cost']), int(row['timeout']),
                float(row['income']), row.get('category', 'shop_logo'),
                heat_generation=gen,
                max_heat=mh,
                conductivity=cond
            ))
    return contents

# --- Box and Grid Classes ---
class Box:
    def __init__(self, row, col, size, origin):
        x = origin[0] + col * size
        y = origin[1] + row * size
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.occupied = False
        self.content = None
        self.row = row
        self.col = col

    def draw(self, surf):
        surf.blit(image_dict['reactor_slot_background'], self.rect)
        if self.content:
            # Draw content image
            surf.blit(self.content.image, self.content.image.get_rect(center=self.rect.center))
            
            # Heat bar
            if not self.content.max_heat == 0:
                ratio_h = min(1.0, max(0.0, self.content.heat / self.content.max_heat))
                pygame.draw.rect(surf, (50, 50, 50), (self.rect.x, self.rect.y+2, self.size, 4))
                pygame.draw.rect(surf, HEAT_COLORS[int(ratio_h * 255)], 
                                (self.rect.x, self.rect.y+2, int(self.size * ratio_h), 4))
            
            # Expiration bar
            if not self.content.permanent:
                elapsed = (pygame.time.get_ticks() - self.content.creation)/1000
                remaining = max(0, self.content.timeout - elapsed)
                ratio = remaining / self.content.timeout
                bar_rect = (self.rect.x, self.rect.y + self.size - 7, self.size, 5)
                pygame.draw.rect(surf, (100, 100, 100), bar_rect)
                
                # Interpolate color
                r = min(1.0, ratio)
                fill_color = (
                    int(255 * (1 - r) + 50 * r),
                    int(165 * (1 - r) + 200 * r),
                    int(0 * (1 - r) + 50 * r)
                )
                pygame.draw.rect(surf, fill_color, 
                                (bar_rect[0], bar_rect[1], int(bar_rect[2] * ratio), bar_rect[3]))

    def is_hovered(self, pos):
        return self.rect.collidepoint(pos)

    def place(self, content):
        if not self.occupied:
            self.occupied = True
            self.content = content.clone()
            r, c = self.row, self.col
            H[r, c] = 0.0
            G[r, c] = self.content.heat_generation
            M[r, c] = self.content.max_heat
            C_arr[r, c] = self.content.conductivity
            return True
        return False

    def remove(self):
        if self.content:
            r, c = self.row, self.col
            H[r, c] = G[r, c] = M[r, c] = C_arr[r, c] = 0.0
        self.occupied = False
        self.content = None

class Grid:
    def __init__(self, rows, cols, size, origin):
        self.cells = [[Box(r, c, size, origin) for c in range(cols)] for r in range(rows)]
        self.flat_cells = [cell for row in self.cells for cell in row]

    def draw(self, surf):
        for cell in self.flat_cells:
            cell.draw(surf)

    def place(self, pos, content):
        for cell in self.flat_cells:
            if cell.is_hovered(pos) and cell.place(content):
                return True
        return False

# --- Shop Classes ---
class ShopBox:
    def __init__(self, pos, size, content):
        self.rect = pygame.Rect(pos[0], pos[1], size, size)
        self.content = content
        self.active = False
        self.font = pygame.font.Font(None, 24)

    def draw(self, surf):
        color = (50, 200, 50) if self.active else (200, 200, 200)
        pygame.draw.rect(surf, color, self.rect, 2)
        surf.blit(self.content.image, self.content.image.get_rect(center=self.rect.center))
        txt = self.font.render(str(self.content.cost), True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(midtop=(self.rect.centerx, self.rect.bottom+4)))

    def is_hovered(self, pos): 
        return self.rect.collidepoint(pos)
    
    def set_active(self, act): 
        self.active = act

class Panel:
    def __init__(self, origin, size, items, cols=6, spacing=20):
        self.boxes = []
        for i, item in enumerate(items):
            r = i // cols
            c = i % cols
            x = origin[0] + c * (size + spacing)
            y = origin[1] + r * (size + spacing)
            self.boxes.append(ShopBox((x, y), size, item))
        if self.boxes: 
            self.boxes[0].set_active(True)

    def draw(self, surf):
        for b in self.boxes: 
            b.draw(surf)

    def handle_click(self, pos, money):
        for b in self.boxes:
            if b.is_hovered(pos) and money >= b.content.cost:
                for o in self.boxes: 
                    o.set_active(o is b)
                return True
        return False

    def get_active(self):
        for b in self.boxes:
            if b.active: 
                return b.content
        return None

class TabBar:
    def __init__(self, tabs, origin, font):
        self.tabs = tabs
        self.active = tabs[0]
        self.font = font
        self.rects = []
        x0, y0 = origin
        w, h = 100, 50
        for i, t in enumerate(tabs):
            self.rects.append((t, pygame.Rect(x0+i*w, y0, w, h)))

    def draw(self, surf):
        for t, rect in self.rects:
            bg = (80, 80, 80) if t == self.active else (30, 30, 30)
            pygame.draw.rect(surf, bg, rect)
            surf.blit(image_dict[f'{t}'], rect)
    
    def handle_click(self, pos):
        for t, rect in self.rects:
            if rect.collidepoint(pos): 
                self.active = t
                return True
        return False

def update_heat_array(H, G, C_arr, M, dt):
    # Create a change array for heat transfers
    dH = np.zeros_like(H)
    rows, cols = H.shape
    
    # Apply diffusion
    for i in range(rows):
        for j in range(cols):
            if M[i, j] <= 0:
                continue
                
            temp_i = H[i, j] / M[i, j]
            
            for di, dj in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and M[ni, nj] > 0:
                    temp_j = H[ni, nj] / M[ni, nj]
                    avg_cond = C_arr[i, j]
                    temp_diff = temp_i - temp_j
                    heat_transfer = dt * avg_cond * temp_diff
                    
                    # Stability limit
                    max_transfer = 0.02 * min(M[i, j], M[ni, nj])
                    heat_transfer = np.clip(heat_transfer, -max_transfer, max_transfer)
                    
                    dH[i, j] -= heat_transfer
                    dH[ni, nj] += heat_transfer
    
    # Apply generation and diffusion
    H += G * dt + dH
    
    # Apply cooling systems
    for i in range(rows):
        for j in range(cols):
            if G[i, j] < 0 and M[i, j] == 0:
                cooling_power = -G[i, j] * dt
                for di, dj in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < rows and 0 <= nj < cols and M[ni, nj] > 0:
                        H[ni, nj] = max(0, H[ni, nj] - cooling_power)
    
    # Clamp values
    np.clip(H, 0, M, out=H)

# Initialize Pygame
pygame.init()
load_images()
screen = pygame.display.set_mode((1000, 800))
pygame.display.set_caption('Idle Grid with Tabs')
font = pygame.font.Font(None, 36)
money_font = pygame.font.Font(None, 28)
money = 500000.0

# Timers

INCOME = pygame.USEREVENT + 1
pygame.time.set_timer(INCOME, game_speed)

# Load items and panels
all_items = load_shop_contents()
cats = ['shop_logo', 'systems_logo', 'upgrade_logo']
panels = {cat: Panel((20, 100), 50, [i for i in all_items if i.category == cat]) for cat in cats}
tabbar = TabBar(cats, (20, 20), font)

# Create grid
grid = Grid(10, 10, 50, (450, 50))

# Heat arrays setup
rows, cols = len(grid.cells), len(grid.cells[0])
H = np.zeros((rows, cols), dtype=float)
G = np.zeros((rows, cols), dtype=float)
M = np.zeros((rows, cols), dtype=float)
C_arr = np.zeros((rows, cols), dtype=float)

# Main loop
running = True
last_time = pygame.time.get_ticks()

while running:
    current_time = pygame.time.get_ticks()
    dt = (current_time - last_time)/game_speed
    last_time = current_time   
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT: 
            running = False
            
        elif e.type == INCOME:

            update_heat_array(H, G, C_arr, M, dt)
            
            for r in range(rows):
                for c in range(cols):
                    b = grid.cells[r][c]
                    if not b.content:
                        continue
                    
                    b.content.heat = H[r, c]
                    money += b.content.income
                    
                    if not b.content.permanent:
                        elapsed = (pygame.time.get_ticks() - b.content.creation)/1000
                        if elapsed >= b.content.timeout:
                            b.remove()
                            continue
                    
                    if b.content.heat >= b.content.max_heat and b.content.heat_generation > 0:
                        b.remove()
                        continue
                        
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            pos = e.pos
            if tabbar.handle_click(pos): 
                continue
                
            panel = panels[tabbar.active]
            if panel.handle_click(pos, money): 
                continue
                
            active = panel.get_active()
            if active and money >= active.cost:
                if grid.place(pos, active): 
                    money -= active.cost
    
    # Rendering
    screen.fill((30, 30, 30))
    grid.draw(screen)
    tabbar.draw(screen)
    panels[tabbar.active].draw(screen)
    screen.blit(money_font.render(f"Money: {round(money)}", True, (255, 215, 0)), (20, 550))
    pygame.display.flip()

pygame.quit()