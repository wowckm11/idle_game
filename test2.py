import pygame
import datetime
import csv
import os

# --- Content Class ---
class Content:
    """
    Represents an item or upgrade available in the shop.
    """
    def __init__(self, name: str, image: pygame.Surface, cost: int, timeout: int, income: float, category: str):
        self.name = name
        self.image = image
        self.cost = cost
        self.timeout = timeout  # seconds
        self.creation = datetime.datetime.now()
        self.income = income
        self.category = category

    def clone(self):
        """
        Create a fresh copy with new timestamp.
        """
        return Content(
            name=self.name,
            image=self.image,
            cost=self.cost,
            timeout=self.timeout,
            income=self.income,
            category=self.category
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
    contents=[]
    with open('shop_objects.csv', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contents.append(Content(row['name'], image_dict.get(row['image']), int(row['cost']),int(row['timeout']), float(row['income']), 'Shop'))
    return contents

# --- Box and Grid Classes ---
class Box:
    """
    Cell in main grid with expiration bar.
    """
    def __init__(self, row, col, size, origin):
        x = origin[0] + col*size
        y = origin[1] + row*size
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.occupied = False
        self.content = None

    def draw(self, surf):
        surf.blit(image_dict['reactor_slot_background'], self.rect)
        if self.content:
            surf.blit(self.content.image, self.content.image.get_rect(center=self.rect.center))
            now = datetime.datetime.now()
            elapsed = (now - self.content.creation).total_seconds()
            remaining = max(0, self.content.timeout - elapsed)
            ratio = remaining/self.content.timeout if self.content.timeout>0 else 0
            bar_h = 5
            bx, by = self.rect.x, self.rect.y + self.size - bar_h - 2
            pygame.draw.rect(surf, (100,100,100), (bx,by,self.size,bar_h))
            green, orange = (50,200,50),(255,165,0)
            fill_color = (
                int(orange[0] + (green[0]-orange[0])*ratio),
                int(orange[1] + (green[1]-orange[1])*ratio),
                int(orange[2] + (green[2]-orange[2])*ratio)
            )
            pygame.draw.rect(surf, fill_color, (bx,by,int(self.size*ratio),bar_h))

    def is_hovered(self, pos): return self.rect.collidepoint(pos)

    def place(self, content):
        if not self.occupied:
            self.occupied = True
            self.content = content.clone()
            return True
        return False

    def remove(self):
        self.occupied=False; self.content=None


class Grid:
    """
    Main play grid.
    """
    def __init__(self, rows, cols, size, origin):
        self.cells = [[Box(r,c,size,origin) for c in range(cols)] for r in range(rows)]

    def draw(self, surf):
        for row in self.cells:
            for b in row: b.draw(surf)

    def place(self, pos, content):
        for row in self.cells:
            for b in row:
                if b.is_hovered(pos) and b.place(content): return True
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

class Panel:
    """
    Displays a grid of ShopBox for one category.
    """
    def __init__(self, origin, size, items, cols=3, spacing=10):
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
        x0,y0=origin; w,h=100,30
        for i,t in enumerate(tabs):
            self.rects.append((t,pygame.Rect(x0+i*w,y0,w,h)))

    def draw(self,surf):
        for t,rect in self.rects:
            bg=(80,80,80) if t==self.active else (30,30,30)
            pygame.draw.rect(surf,bg,rect)
            txt=self.font.render(t,True,(255,255,255))
            surf.blit(txt,txt.get_rect(center=rect.center))

    def handle_click(self,pos):
        for t,rect in self.rects:
            if rect.collidepoint(pos): self.active=t; return True
        return False

# Shop logo rect
shop_logo_rect = pygame.Rect(50, 0, 50, 100)

pygame.init()
load_images()
screen=pygame.display.set_mode((800,600))
pygame.display.set_caption('Idle Grid with Tabs')
font=pygame.font.Font(None,36)
money_font=pygame.font.Font(None,28)
money=500.0
# timers
INCOME=pygame.USEREVENT+1
pygame.time.set_timer(INCOME,1000)
# load items and panels
all_items=load_shop_contents()
cats=['Shop','Infrastructure','Upgrades']
panels={cat:Panel((20,60),50,[i for i in all_items if i.category==cat]) for cat in cats}
tabbar=TabBar(cats,(20,20),font)
grid=Grid(10,10,50,(200,50))
# main loop
running=True
while running:
    now=datetime.datetime.now()
    for e in pygame.event.get():
        if e.type==pygame.QUIT: running=False
        elif e.type==INCOME:
            for row in grid.cells:
                for b in row:
                    if b.content:
                        money+=b.content.income
                        if (now-b.content.creation).total_seconds()>=b.content.timeout:
                            b.remove()
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
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
