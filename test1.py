import pygame
import csv
import os
import numpy as np
from scipy.ndimage import label

# Pre-calculate heat colors
HEAT_COLORS = [(int(255 * r), int(255 * (1 - r)), 0) for r in np.linspace(0, 1, 256)]

#config
game_speed_actions_per_second=50
diffusion_rate_factor_setting=1
return_percentage_on_sell = 1

# --- Content Class ---
class Content:
    def __init__(self, name: str, image: pygame.Surface, cost: int,
                 timeout: int, income: float, category: str,
                 heat_generation: float = 0.0, max_heat: float = 5.0,
                 conductivity: float = 0.0):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout
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
            income=self.income/game_speed_actions_per_second,
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
            image_list.append((f'assets/{row["name"]}.png', row['name']))
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
            img = image_dict.get(row['name'])
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

    def cash_return(self):
        if self.content:
            return self.content.cost

class Grid:
    def __init__(self, rows, cols, size, origin):
        self.rows = rows # Store rows for bounds checking
        self.cols = cols # Store cols for bounds checking
        self.cell_size = size # Store cell size for calculations
        self.origin = origin # Store origin for calculations
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

    def get_cell_at_pos(self, pos):
        """
        Returns the Box (cell) at the given mouse position, or None if no cell is at that position.
        """
        mouse_x, mouse_y = pos
        origin_x, origin_y = self.origin

        # Adjust mouse position relative to the grid's origin
        relative_x = mouse_x - origin_x
        relative_y = mouse_y - origin_y

        # Calculate which column and row the adjusted mouse position falls into
        col = relative_x // self.cell_size
        row = relative_y // self.cell_size

        # Check if the calculated row and column are within the grid bounds
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[int(row)][int(col)] # Ensure row/col are integers for indexing
        return None

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
    """
    Updates the heat distribution in a 2D grid based on heat generation/loss,
    heat transfer between adjacent cells, and cooling systems.

    Parameters:
    H (np.array): 2D numpy array representing the current heat content of each cell.
    G (np.array): 2D numpy array representing the heat generation/loss rate for each cell.
                  Positive values generate heat, negative values remove heat.
    C_arr (np.array): 2D numpy array representing the conductivity of each cell.
                      Used to determine heat transfer rates between cells.
    M (np.array): 2D numpy array representing the heat capacity of each cell.
                  Also acts as a maximum heat content for clamping.
    dt (float): Time step for the simulation.

    Returns:
    np.array: The updated heat content array H after one time step.
    """

    # Apply heat generation/loss first
    # H is modified in-place
    H += G * dt

    # Create a temperature matrix (heat per capacity)
    # Cells with M <= 0 will have T = 0 to avoid division by zero.
    T = np.divide(H, M, out=np.zeros_like(H, dtype=float), where=M > 0)

    # Initialize a delta heat array to accumulate changes for this timestep.
    # This is crucial for ensuring all heat transfer calculations for the current
    # timestep are based on the temperatures at the *beginning* of the timestep.
    # Changes are applied simultaneously at the end of the heat transfer loop.
    dH = np.zeros_like(H, dtype=float)

    rows, cols = H.shape

    # Define 4-connected neighbors for heat transfer.
    # Heat typically flows between directly adjacent cells.
    neighbors_coords = [(0, 1), (1, 0), (0, -1), (-1, 0)] # Right, Down, Left, Up

    # Create a connectivity matrix (cells that can exchange heat).
    # Cells are considered connected if their conductivity (C_arr) is greater than 0.
    connectivity = (C_arr > 0).astype(int)

    # Identify connected components using scipy.ndimage.label.
    # This groups cells that can potentially exchange heat into distinct components.
    # The structure parameter defines 8-connectedness for component labeling.
    structure = np.ones((3, 3), dtype=int) # 8-connected for component identification
    labeled, num_features = label(connectivity, structure=structure)

    # --- Heat Transfer by Edges (Local Diffusion) ---
    # Iterate over each cell in the grid to calculate heat flow to its neighbors
    for r in range(rows):
        for c in range(cols):
            # Only consider cells that have heat capacity and can conduct heat.
            # Cells with M <= 0 or C_arr <= 0 cannot participate in heat transfer.
            if M[r, c] <= 0 or C_arr[r, c] <= 0:
                continue

            current_temp = T[r, c]
            current_conductivity = C_arr[r, c]
            
            # Iterate over 4-connected neighbors
            for dr, dc in neighbors_coords:
                nr, nc = r + dr, c + dc

                # Check if neighbor is within grid bounds
                if 0 <= nr < rows and 0 <= nc < cols:
                    # Check if the neighbor also has heat capacity and can conduct heat
                    if M[nr, nc] > 0 and C_arr[nr, nc] > 0:
                        # Ensure both cells are part of the *same* connected component.
                        # Heat should not flow between cells in different isolated components.
                        # labeled[r,c] == 0 means the cell has no conductivity and is not part of any component.
                        if labeled[r, c] != 0 and labeled[r, c] == labeled[nr, nc]:
                            neighbor_temp = T[nr, nc]
                            neighbor_conductivity = C_arr[nr, nc]

                            # Calculate effective conductivity between the two cells.
                            # The heat flow is limited by the less conductive of the two cells,
                            # acting as a bottleneck.
                            effective_conductivity = (current_conductivity+neighbor_conductivity)/2

                            # Calculate temperature difference.
                            # Heat flows from the hotter cell to the colder cell.
                            # If current_temp > neighbor_temp, heat flows from (r,c) to (nr,nc).
                            temp_diff = current_temp - neighbor_temp

                            # Define a diffusion rate factor. This can be tuned for stability
                            # and the speed of diffusion. It's similar to the '0.2' factor
                            # from your original code's max_temp_change.
                            diffusion_rate_factor = diffusion_rate_factor_setting # Tune this value as needed

                            # Calculate the amount of heat flowing from (r,c) to (nr,nc)
                            # This is a simplified form of Fourier's Law.
                            heat_flow = effective_conductivity * temp_diff * dt * diffusion_rate_factor

                            # Accumulate heat changes in the dH array.
                            # The current cell (r,c) loses heat, the neighbor (nr,nc) gains heat.
                            dH[r, c] -= heat_flow
                            dH[nr, nc] += heat_flow
    
    # Apply all accumulated heat changes simultaneously to the H array.
    H += dH

    # --- Apply Cooling Systems ---
    # This section handles specific cooling cells (where G < 0 and M == 0).
    # These cells themselves have no heat capacity but act as heat sinks for neighbors.
    cooling_mask = (G < 0) & (M == 0)
    cooling_cells = np.argwhere(cooling_mask)

    for i, j in cooling_cells:
        # Calculate the total cooling power from this specific cooling cell.
        cooling_power = -G[i, j] * dt # G[i,j] is negative, so -G[i,j] is positive power
        
        neighbors_to_cool = []
        # Find all valid 4-connected neighbors that have heat capacity (M > 0)
        for di, dj in neighbors_coords:
            ni, nj = i + di, j + dj
            if 0 <= ni < rows and 0 <= nj < cols and M[ni, nj] > 0:
                neighbors_to_cool.append((ni, nj))
        
        # Distribute the cooling power among the coolable neighbors.
        if neighbors_to_cool:
            # Calculate the total heat of only the neighbors that can be cooled.
            total_heat_of_coolable_neighbors = sum(H[n] for n in neighbors_to_cool)
            
            # Only cool if there's heat to remove from neighbors.
            if total_heat_of_coolable_neighbors > 0:
                for ni, nj in neighbors_to_cool:
                    # Proportionally cool based on the neighbor's current heat content.
                    proportion = H[ni, nj] / total_heat_of_coolable_neighbors
                    cool_amount = cooling_power * proportion

                    # Ensure heat content does not drop below zero.
                    H[ni, nj] = max(0, H[ni, nj] - cool_amount)
    
    # --- Final Clamping ---
    # Clamp heat values to a valid range:
    # - Ensure heat content is non-negative.
    # - Ensure heat content does not exceed the cell's maximum capacity (M).
    #   (Assuming M also represents the maximum allowable heat content).
    np.clip(H, 0, M, out=H)

    return H

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
pygame.time.set_timer(INCOME, 1000//game_speed_actions_per_second)

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
    dt = (current_time - last_time)/game_speed_actions_per_second
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
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:  
            pos = e.pos
            # Find the cell at the mouse position and remove its content
            cell_clicked = grid.get_cell_at_pos(pos)
            if cell_clicked and cell_clicked.content:
                money += cell_clicked.cash_return()*return_percentage_on_sell
                cell_clicked.remove() # This should now remove the content of the clicked cell
    # Rendering
    screen.fill((30, 30, 30))
    grid.draw(screen)
    tabbar.draw(screen)
    panels[tabbar.active].draw(screen)
    screen.blit(money_font.render(f"Money: {round(money)}", True, (255, 215, 0)), (20, 550))
    pygame.display.flip()

pygame.quit()