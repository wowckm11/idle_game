import pygame
import datetime
import csv
import os
import numpy as np
from scipy.signal import convolve2d

# --- Content Class ---
class Content:
    """
    Represents an item or upgrade available in the shop.
    """
    def __init__(self, name: str, image: pygame.Surface, cost: int,
                 timeout: int, income: float, category: str,
                 heat_generation: float = 0.0, max_heat: float = 5.0,
                 conductivity: float = 0.0):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout  # seconds
        self.creation = datetime.datetime.now()
        self.income = income
        self.category = category
        # Heat properties
        self.heat = 0.0
        self.heat_generation = heat_generation  # units per second
        self.max_heat = max_heat
        self.conductivity = conductivity  # heat transfer rate
        self.permanent = (timeout == 0)

    def clone(self):
        """
        Create a fresh copy with new timestamp, preserving heat settings.
        """
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
            # parse new heat fields
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
    """
    Cell in main grid with expiration and heat bars.
    """
    def __init__(self, row, col, size, origin):
        x = origin[0] + col * size
        y = origin[1] + row * size
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.occupied = False
        self.content = None
        # Store grid coordinates for diffusion mapping
        self.row = row
        self.col = col

    def draw(self, surf):
        surf.blit(image_dict['reactor_slot_background'], self.rect)
        if self.content:
            # Draw content image
            surf.blit(
                self.content.image,
                self.content.image.get_rect(center=self.rect.center)
            )
            # Heat bar at top
            ratio_h = (
                self.content.heat / self.content.max_heat
                if self.content.max_heat > 0 else 0
            )
            hb_h = 4
            hb_x = self.rect.x
            hb_y = self.rect.y + 2
            # Background of heat bar
            pygame.draw.rect(
                surf, (50, 50, 50),
                (hb_x, hb_y, self.size, hb_h)
            )
            # Color from green to red
            heat_color = (
                int(255 * ratio_h),
                int(255 * (1 - ratio_h)),
                0
            )
            pygame.draw.rect(
                surf, heat_color,
                (hb_x, hb_y, int(self.size * ratio_h), hb_h)
            )
            # Expiration bar at bottom (skip if permanent)
            if not self.content.permanent:
                now = datetime.datetime.now()
                elapsed = (now - self.content.creation).total_seconds()
                remaining = max(0, self.content.timeout - elapsed)
                ratio = (
                    remaining / self.content.timeout
                    if self.content.timeout > 0 else 0
                )
                bar_h = 5
                bx, by = self.rect.x, self.rect.y + self.size - bar_h - 2
                pygame.draw.rect(
                    surf, (100, 100, 100),
                    (bx, by, self.size, bar_h)
                )
                green, orange = (50, 200, 50), (255, 165, 0)
                fill_color = (
                    int(orange[0] + (green[0] - orange[0]) * ratio),
                    int(orange[1] + (green[1] - orange[1]) * ratio),
                    int(orange[2] + (green[2] - orange[2]) * ratio)
                )
                pygame.draw.rect(
                    surf, fill_color,
                    (bx, by, int(self.size * ratio), bar_h)
                ),
                (bx, by, self.size, bar_h)

                green, orange = (50, 200, 50), (255, 165, 0)
                fill_color = (
                    int(orange[0] + (green[0] - orange[0]) * ratio),
                    int(orange[1] + (green[1] - orange[1]) * ratio),
                    int(orange[2] + (green[2] - orange[2]) * ratio)
                )
                pygame.draw.rect(
                    surf, fill_color,
                    (bx, by, int(self.size * ratio), bar_h)
                )

    def is_hovered(self, pos):
        return self.rect.collidepoint(pos)

    def place(self, content):
        if not self.occupied:
            self.occupied = True
            self.content = content.clone()
            # Populate heat arrays
            global H, G, M, C_arr
            r, c = self.row, self.col
            H[r, c] = 0.0
            G[r, c] = self.content.heat_generation
            M[r, c] = self.content.max_heat
            C_arr[r, c] = self.content.conductivity
            return True
        return False
        return False

    def remove(self):
        # Clear heat arrays on removal
        global H, G, M, C_arr
        if self.content:
            r, c = self.row, self.col
            H[r, c] = 0.0
            G[r, c] = 0.0
            M[r, c] = 0.0
            C_arr[r, c] = 0.0
        self.occupied = False
        self.content = None

class Grid:
    """
    Main play grid.
    """
    def __init__(self, rows, cols, size, origin):
        self.cells = [
            [Box(r, c, size, origin) for c in range(cols)]
            for r in range(rows)
        ]

    def draw(self, surf):
        for row in self.cells:
            for b in row:
                b.draw(surf)

    def place(self, pos, content):
        for row in self.cells:
            for b in row:
                if b.is_hovered(pos) and b.place(content):
                    return True
        return False

# --- Shop Classes ---
class ShopBox:
    """
    Cell in a panel.
    """
    def __init__(self, pos, size, content):
        self.rect=pygame.Rect(pos[0],pos[1],size,size)
        self.content=content; self.active=False
        self.font=pygame.font.Font(None,24)

    def draw(self,surf):
        color=(50,200,50) if self.active else (200,200,200)
        pygame.draw.rect(surf,color,self.rect,2)
        surf.blit(self.content.image,self.content.image.get_rect(center=self.rect.center))
        txt=self.font.render(str(self.content.cost),True,(255,255,255))
        surf.blit(txt,txt.get_rect(midtop=(self.rect.centerx,self.rect.bottom+4)))

    def is_hovered(self,pos): return self.rect.collidepoint(pos)
    def set_active(self,act): self.active=act


class Shop:
    """
    A layout of ShopBox items in rows of 3 per line.
    """
    def __init__(self, origin: tuple, box_size: int, contents: list, spacing: int = 20, items_per_row: int = 4):
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

class Panel:
    """
    Displays a grid of ShopBox for one category.
    """
    def __init__(self, origin, size, items, cols=6, spacing=20):
        self.boxes=[]
        for i,item in enumerate(items):
            r=i//cols; c=i%cols
            x=origin[0]+c*(size+spacing)
            y=origin[1]+r*(size+spacing)
            b=ShopBox((x,y),size,item)
            self.boxes.append(b)
        if self.boxes: self.boxes[0].set_active(True)

    def draw(self,surf):
        for b in self.boxes: b.draw(surf)

    def handle_click(self,pos,money):
        for b in self.boxes:
            if b.is_hovered(pos) and money>=b.content.cost:
                for o in self.boxes: o.set_active(o is b)
                return True
        return False

    def get_active(self):
        for b in self.boxes:
            if b.active: return b.content
        return None


class TabBar:
    """
    Renders and tracks tabs.
    """
    def __init__(self,tabs,origin,font):
        self.tabs=tabs; self.active=tabs[0]; self.font=font
        self.rects=[]
        x0,y0=origin; w,h=100,50
        for i,t in enumerate(tabs):
            self.rects.append((t,pygame.Rect(x0+i*w,y0,w,h)))

    def draw(self,surf):
        for t,rect in self.rects:
            bg=(80,80,80) if t==self.active else (30,30,30)
            txt=pygame.draw.rect(surf,bg,rect)
            surf.blit(image_dict[f'{t}'],txt)
    def handle_click(self,pos):
        for t,rect in self.rects:
            if rect.collidepoint(pos): self.active=t; return True
        return False

# Shop logo rect

pygame.init()
load_images()
screen=pygame.display.set_mode((1000,800))
pygame.display.set_caption('Idle Grid with Tabs')
font=pygame.font.Font(None,36)
money_font=pygame.font.Font(None,28)
money=500.0
# timers
INCOME=pygame.USEREVENT+1
pygame.time.set_timer(INCOME,100)
# load items and panels
all_items=load_shop_contents()
cats=['shop_logo','systems_logo','upgrade_logo']
panels={cat:Panel((20,100),50,[i for i in all_items if i.category==cat]) for cat in cats}
tabbar=TabBar(cats,(20,20),font)
# create grid
grid=Grid(10,10,50,(450,50))
# --- Heat arrays setup ---
rows, cols = len(grid.cells), len(grid.cells[0])
H = np.zeros((rows, cols), dtype=float)
G = np.zeros((rows, cols), dtype=float)
M = np.zeros((rows, cols), dtype=float)
C_arr = np.zeros((rows, cols), dtype=float)  # conductivity array

# Laplacian kernel for diffusion
lap_kernel = np.array([[0,1,0], [1,-4,1], [0,1,0]], dtype=float)


def update_heat_array(H, G, C_arr, M, dt):
    # Create a copy of H for read-only purposes
    H_old = H.copy()
    
    # Apply heat generation first
    H[:] = H_old + G * dt
    
    # Create a change array to accumulate heat transfers
    dH = np.zeros_like(H)
    
    # Apply diffusion using finite differences based on temperature
    rows, cols = H.shape
    for i in range(rows):
        for j in range(cols):
            # Skip empty cells (no heat capacity)
            if M[i, j] <= 0:
                continue
                
            # Calculate current temperature for this cell
            temp_i = H[i, j] / M[i, j]
            
            # Check all 4 neighbors
            for di, dj in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols:
                    # Skip empty neighbors
                    if M[ni, nj] <= 0:
                        continue
                    
                    # Calculate neighbor temperature
                    temp_j = H[ni, nj] / M[ni, nj]
                    
                    # Calculate heat transfer based on average conductivity and temp difference
                    avg_conductivity = (C_arr[i, j] + C_arr[ni, nj]) / 2
                    temp_diff = temp_i - temp_j
                    heat_transfer = dt * avg_conductivity * temp_diff
                    
                    # Optional: Add a max heat transfer limit for stability
                    max_transfer = 0.5
                    heat_transfer = np.clip(heat_transfer, -max_transfer, max_transfer)
                    
                    # Apply transfer to neighbor
                    dH[ni, nj] += heat_transfer
                    # Apply opposite change to current cell
                    dH[i, j] -= heat_transfer
                    
            for i in range(rows):
                for j in range(cols):
                    if G[i, j] < 0 and M[i, j] == 0:
                        removal = -G[i, j] * dt
                        # remove from neighbors
                        for di, dj in [(0,1),(1,0),(0,-1),(-1,0)]:
                            ni, nj = i + di, j + dj
                            if 0 <= ni < rows and 0 <= nj < cols:
                                H[ni, nj] = max(0.0, H[ni, nj] - removal)
    # Apply the accumulated heat changes
    H += dH
    
    # Clamp values to valid range
    np.clip(H, 0, M, out=H)

# main loop
running=True
while running:
    now=datetime.datetime.now()
    for e in pygame.event.get():
        if e.type==pygame.QUIT: running=False
        elif e.type==INCOME:
            # Vectorized heat update
            dt = 0.1  # seconds per tick
            update_heat_array(H, G, C_arr, M, dt)
            # Sync back to each box and handle income/expiration/overflow
            now = datetime.datetime.now()
            for r in range(rows):
                for c in range(cols):
                    b = grid.cells[r][c]
                    if not b.content:
                        continue
                    # Sync heat value
                    b.content.heat = H[r, c]
                    # Accrue income
                    money += b.content.income
                    # Expire non-permanent items
                    if not b.content.permanent:
                        elapsed = (now - b.content.creation).total_seconds()
                        if elapsed >= b.content.timeout:
                            b.remove()
                            # clear arrays
                            H[r, c] = G[r, c] = M[r, c] = C_arr[r, c] = 0.0
                            continue
                    # Remove on heat overflow
                    if b.content.heat >= b.content.max_heat:
                        b.remove()
                        H[r, c] = G[r, c] = M[r, c] = C_arr[r, c] = 0.0
                        continue
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and e.button==1:
            pos=e.pos
            if tabbar.handle_click(pos): continue
            panel=panels[tabbar.active]
            if panel.handle_click(pos,money): continue
            active=panel.get_active()
            if active and money>=active.cost:
                if grid.place(pos,active): money-=active.cost
    screen.fill((30,30,30))
    grid.draw(screen)
    tabbar.draw(screen)
    panels[tabbar.active].draw(screen)
    screen.blit(money_font.render(f"Money: {round(money)}",True,(255,215,0)),(20,550))
    pygame.display.flip()
pygame.quit()
