
import pygame
import sys
import time
import random
import io
import contextlib
from datetime import datetime

# ==========================================
# THEME & CONFIGURATION
# ==========================================
THEME = {
    "desktop_bg": (11, 12, 16),       # Deep Indigo
    "taskbar_bg": (31, 40, 51),       # Slate
    "window_bg": (20, 25, 30),        # Dark Slate
    "title_bar": (31, 40, 51),        # Slate
    "title_bar_active": (69, 162, 158),# Teal
    "accent": (102, 252, 241),        # Neon Cyan
    "text_main": (197, 198, 199),     # Silver
    "text_dark": (11, 12, 16),        # Dark for active title bars
    "danger": (255, 65, 85),          # Red for close buttons
    "code_bg": (15, 18, 22),          # Darker BG for code/terminal
    "code_keyword": (198, 120, 221)   # Purple for code highlights
}

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
TASKBAR_HEIGHT = 40

# ==========================================
# MODULAR CPU ARCHITECTURE (Virtual Machine)
# ==========================================
class Memory:
    def __init__(self, size):
        self.data = [0] * size
    def read(self, addr): return self.data[addr % len(self.data)]
    def write(self, addr, val): self.data[addr % len(self.data)] = val & 0xFF

class ALU:
    def execute(self, op, v1, v2):
        if op == "ADD": return (v1 + v2) & 0xFF
        if op == "SUB": return (v1 - v2) & 0xFF
        if op == "MUL": return (v1 * v2) & 0xFF
        if op == "AND": return v1 & v2
        if op == "OR":  return v1 | v2
        if op == "XOR": return v1 ^ v2
        if op == "BSL": return (v1 << v2) & 0xFF
        return 0

class ModularCPU:
    def __init__(self, rom_data):
        self.core_id = 0
        self.regs = [0] * 8
        self.pc = 0
        self.rom = rom_data
        self.ram = Memory(256)
        self.ports = [0] * 256
        self.screen = [[0]*32 for _ in range(32)]
        self.pipeline = {"F": None, "D": None, "E": None, "W": None}
        self.alu = ALU()

    def resolve(self, op):
        if isinstance(op, str) and op.startswith("R"):
            if self.pipeline["W"] and self.pipeline["W"][1] == op:
                return self.pipeline["W"][0]
            return self.regs[int(op[1:])]
        return int(op) if op is not None else 0

    def tick(self):
        # 1. WRITEBACK
        if self.pipeline["W"]:
            val, target = self.pipeline["W"]
            if isinstance(target, str) and target.startswith("R"):
                self.regs[int(target[1:])] = val

        # 2. EXECUTE
        self.pipeline["W"] = None
        if self.pipeline["E"]:
            op, dest, arg1, arg2 = self.pipeline["E"]
            v1, v2 = self.resolve(arg1), self.resolve(arg2)

            if op == "OUT":
                port = self.resolve(dest)
                self.ports[port % 256] = v1
                if port == 0: self.pipeline["W"] = (self.core_id, dest)
                if port == 12: self.screen[self.ports[11]%32][self.ports[10]%32] = 1
                if port == 13: self.screen = [[0]*32 for _ in range(32)]
            elif op == "JMP":
                self.pc = v2
                self.pipeline["F"] = self.pipeline["D"] = None
            elif op == "BEQ":
                if self.resolve(dest) == v1:
                    self.pc = v2
                    self.pipeline["F"] = self.pipeline["D"] = None
            else:
                self.pipeline["W"] = (self.alu.execute(op, v1, v2), dest)

        # 3. PIPELINE MOVE
        self.pipeline["E"] = self.pipeline["D"]
        self.pipeline["D"] = self.pipeline["F"]

        # 4. FETCH
        if self.pc < len(self.rom) and self.rom[self.pc]:
            self.pipeline["F"] = self.rom[self.pc]
            self.pc += 1
        else:
            self.pipeline["F"] = None


# ==========================================
# APPLICATION BASE CLASS
# ==========================================
class Application:
    NAME = "Unknown App"
    DEFAULT_SIZE = (400, 300)
    MEMORY_FOOTPRINT = 10

    def __init__(self, os_kernel, window):
        self.os = os_kernel
        self.window = window
        self.load = 0.0 # CPU Load %

    def handle_event(self, event, local_mouse_pos): pass
    def update(self): pass
    def draw(self, surface): surface.fill(THEME["window_bg"])


# ==========================================
# BUILT-IN APPLICATIONS
# ==========================================
class TerminalApp(Application):
    NAME = "Nexus Terminal"
    DEFAULT_SIZE = (450, 300)
    MEMORY_FOOTPRINT = 12

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_mono
        self.scrollback = [
            "Aethel OS: Nexus [Version 2.0]",
            "Type 'help' for available commands.", ""
        ]
        self.current_input = ""
        self.blink_timer = 0

    def handle_event(self, event, local_mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.process_command(self.current_input)
                self.current_input = ""
            elif event.key == pygame.K_BACKSPACE:
                self.current_input = self.current_input[:-1]
            elif event.unicode.isprintable():
                self.current_input += event.unicode

    def process_command(self, cmd):
        self.scrollback.append(f"admin@nexus:~$ {cmd}")
        cmd = cmd.strip().lower()
        parts = cmd.split(" ")

        if cmd == "help":
            self.scrollback.extend(["Commands: help, clear, ps, time, echo [text]"])
        elif cmd == "clear":
            self.scrollback = []
        elif cmd == "time":
            self.scrollback.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        elif cmd == "ps":
            self.scrollback.append("PID  MEM   CPU%   WINDOW TITLE")
            for i, win in enumerate(self.os.windows):
                self.scrollback.append(f"{i:<4} {win.app.MEMORY_FOOTPRINT:<3}MB {win.app.load:>4.1f}% {win.title}")
        elif cmd.startswith("echo "):
            self.scrollback.append(" ".join(parts[1:]))
        elif cmd != "":
            self.scrollback.append(f"Command not found: {parts[0]}")
        self.scrollback.append("") 

    def update(self):
        self.blink_timer = (self.blink_timer + 1) % 60

    def draw(self, surface):
        super().draw(surface)
        y_offset = surface.get_height() - 25
        cursor = "_" if self.blink_timer < 30 else " "
        prompt = f"admin@nexus:~$ {self.current_input}{cursor}"
        surface.blit(self.font.render(prompt, True, THEME["accent"]), (10, y_offset))
        
        y_offset -= 20
        for line in reversed(self.scrollback):
            if y_offset < 0: break
            surface.blit(self.font.render(line, True, THEME["text_main"]), (10, y_offset))
            y_offset -= 20


class TaskManagerApp(Application):
    NAME = "Task Manager"
    DEFAULT_SIZE = (450, 320)
    MEMORY_FOOTPRINT = 16

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_main
        self.history = [0.0] * 50
        self.tick = 0

    def update(self):
        self.tick += 1
        if self.tick % 5 == 0:
            self.history.pop(0)
            self.history.append(self.os.cpu_load)

    def draw(self, surface):
        super().draw(surface)
        w, h = surface.get_size()
        
        surface.blit(self.font.render("System Load & Processes", True, THEME["accent"]), (10, 10))

        # Graph Background
        graph_rect = pygame.Rect(10, 35, w - 20, 80)
        pygame.draw.rect(surface, THEME["code_bg"], graph_rect)
        pygame.draw.rect(surface, THEME["title_bar"], graph_rect, 2)

        max_val = max(5.0, max(self.history)) 
        points = []
        step_x = graph_rect.width / max(1, len(self.history) - 1)
        for i, val in enumerate(self.history):
            x = graph_rect.left + (i * step_x)
            y = graph_rect.bottom - (val / max_val * graph_rect.height)
            points.append((x, y))
        
        if len(points) > 1:
            pygame.draw.lines(surface, THEME["accent"], False, points, 2)

        current_load = self.history[-1]
        stat_text = self.font.render(f"Global CPU: {current_load:.1f}% | RAM: {self.os.get_ram_usage()}/{self.os.max_ram} MB", True, THEME["text_main"])
        surface.blit(stat_text, (10, 125))

        # Process List
        list_rect = pygame.Rect(10, 150, w - 20, h - 160)
        pygame.draw.rect(surface, THEME["code_bg"], list_rect)
        pygame.draw.rect(surface, THEME["title_bar"], list_rect, 2)
        
        headers = self.font.render("PID   PROCESS NAME            RAM       CPU%", True, THEME["accent"])
        surface.blit(headers, (15, 155))
        pygame.draw.line(surface, THEME["title_bar"], (15, 175), (w-15, 175))

        y_off = 180
        for i, win in enumerate(self.os.windows):
            p_text = f"{i:<5} {win.title[:20]:<23} {win.app.MEMORY_FOOTPRINT:>3}MB     {win.app.load:>4.1f}%"
            surface.blit(self.os.font_mono.render(p_text, True, THEME["text_main"]), (15, y_off))
            y_off += 20


class CodeEditorApp(Application):
    NAME = "CodePad (Python)"
    DEFAULT_SIZE = (500, 420)
    MEMORY_FOOTPRINT = 32

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_mono
        self.lines = ["print('Hello, Nexus OS!')", "for i in range(3):", "    print(f'Loop {i}')", ""]
        self.cx, self.cy = 0, 0
        self.output = []
        self.blink = 0

    def handle_event(self, event, local_mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            btn_rect = pygame.Rect(10, 10, 60, 25)
            if btn_rect.collidepoint(local_mouse_pos):
                self.execute_code()
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.cy = max(0, self.cy - 1)
                self.cx = min(self.cx, len(self.lines[self.cy]))
            elif event.key == pygame.K_DOWN:
                self.cy = min(len(self.lines) - 1, self.cy + 1)
                self.cx = min(self.cx, len(self.lines[self.cy]))
            elif event.key == pygame.K_LEFT:
                if self.cx > 0: self.cx -= 1
                elif self.cy > 0:
                    self.cy -= 1
                    self.cx = len(self.lines[self.cy])
            elif event.key == pygame.K_RIGHT:
                if self.cx < len(self.lines[self.cy]): self.cx += 1
                elif self.cy < len(self.lines) - 1:
                    self.cy += 1
                    self.cx = 0
            elif event.key == pygame.K_RETURN:
                curr = self.lines[self.cy]
                self.lines[self.cy] = curr[:self.cx]
                self.lines.insert(self.cy + 1, curr[self.cx:])
                self.cy += 1
                self.cx = 0
            elif event.key == pygame.K_BACKSPACE:
                if self.cx > 0:
                    curr = self.lines[self.cy]
                    self.lines[self.cy] = curr[:self.cx-1] + curr[self.cx:]
                    self.cx -= 1
                elif self.cy > 0:
                    curr = self.lines.pop(self.cy)
                    self.cy -= 1
                    self.cx = len(self.lines[self.cy])
                    self.lines[self.cy] += curr
            elif event.unicode.isprintable() and not event.key == pygame.K_TAB:
                curr = self.lines[self.cy]
                self.lines[self.cy] = curr[:self.cx] + event.unicode + curr[self.cx:]
                self.cx += 1
            elif event.key == pygame.K_TAB:
                curr = self.lines[self.cy]
                self.lines[self.cy] = curr[:self.cx] + "    " + curr[self.cx:]
                self.cx += 4

    def execute_code(self):
        code = "\n".join(self.lines)
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            try:
                # Provide a restricted safe environment if desired, or let it have full power
                exec(code, {"math": __import__("math"), "random": __import__("random")})
            except Exception as e:
                print(f"Error: {e}")
        
        self.output = f.getvalue().split("\n")

    def update(self):
        self.blink = (self.blink + 1) % 60

    def draw(self, surface):
        super().draw(surface)
        w, h = surface.get_size()
        
        # Toolbar
        btn_rect = pygame.Rect(10, 10, 60, 25)
        pygame.draw.rect(surface, (40, 180, 100), btn_rect, border_radius=4)
        surface.blit(self.os.font_bold.render("RUN", True, THEME["text_dark"]), (25, 14))

        # Editor Area
        ed_rect = pygame.Rect(10, 45, w - 20, h - 180)
        pygame.draw.rect(surface, THEME["code_bg"], ed_rect)
        pygame.draw.rect(surface, THEME["title_bar"], ed_rect, 2)

        y_off = 50
        for i, line in enumerate(self.lines):
            # Render Line Numbers
            num_surf = self.font.render(str(i+1), True, (100, 100, 110))
            surface.blit(num_surf, (15, y_off))
            # Render Text
            text_surf = self.font.render(line, True, THEME["text_main"])
            surface.blit(text_surf, (45, y_off))
            
            # Cursor
            if i == self.cy and self.blink < 30:
                cx_px = 45 + self.font.size(line[:self.cx])[0]
                pygame.draw.line(surface, THEME["accent"], (cx_px, y_off + 2), (cx_px, y_off + 16), 2)
            
            y_off += 18
            if y_off > ed_rect.bottom - 20: break

        # Output Area
        out_rect = pygame.Rect(10, h - 125, w - 20, 115)
        pygame.draw.rect(surface, (5, 5, 8), out_rect)
        pygame.draw.rect(surface, THEME["title_bar"], out_rect, 2)
        surface.blit(self.font.render("Console Output:", True, (100, 100, 100)), (15, h - 120))
        
        y_off = h - 100
        for line in self.output[-5:]:  # Show last 5 lines
            surface.blit(self.font.render(line, True, THEME["accent"]), (15, y_off))
            y_off += 16


class BrowserApp(Application):
    NAME = "Nexus Browser"
    DEFAULT_SIZE = (500, 400)
    MEMORY_FOOTPRINT = 45

    PAGES = {
        "nexus://home": [
            "Welcome to Nexus Browser v1.0",
            "-----------------------------",
            "A fast, lightweight portal to the digital void.",
            "",
            "Try visiting:",
            "  - nexus://about",
            "  - nexus://help"
        ],
        "nexus://about": [
            "About Nexus Browser",
            "-----------------------------",
            "Developed by Aethel OS Systems.",
            "Rendering Engine: TextCanvas 1.0",
            "Secure connection: ENABLED"
        ],
        "nexus://help": [
            "Need Help?",
            "-----------------------------",
            "Just click the URL bar at the top, type your",
            "destination, and press ENTER."
        ]
    }

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_mono
        self.url = "nexus://home"
        self.input_url = self.url
        self.focused = False
        self.content = self.PAGES[self.url]

    def handle_event(self, event, local_mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            url_rect = pygame.Rect(10, 10, self.window.rect.width - 20, 30)
            self.focused = url_rect.collidepoint(local_mouse_pos)
        
        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_RETURN:
                self.load_page(self.input_url)
                self.focused = False
            elif event.key == pygame.K_BACKSPACE:
                self.input_url = self.input_url[:-1]
            elif event.unicode.isprintable():
                self.input_url += event.unicode

    def load_page(self, url):
        self.url = url
        if url in self.PAGES:
            self.content = self.PAGES[url]
        else:
            self.content = [f"404 - '{url}' Not Found.", "DNS Resolution failed in Nexus Network."]

    def draw(self, surface):
        super().draw(surface)
        w, h = surface.get_size()

        # URL Bar
        url_rect = pygame.Rect(10, 10, w - 20, 30)
        color = THEME["accent"] if self.focused else THEME["title_bar"]
        pygame.draw.rect(surface, THEME["code_bg"], url_rect)
        pygame.draw.rect(surface, color, url_rect, 2)
        
        display_url = self.input_url + ("|" if self.focused and (pygame.time.get_ticks() // 500 % 2) else "")
        surface.blit(self.font.render(display_url, True, THEME["text_main"]), (15, 16))

        # Content Area
        y_off = 60
        for line in self.content:
            surface.blit(self.font.render(line, True, THEME["text_main"]), (15, y_off))
            y_off += 20


class SnakeApp(Application):
    NAME = "Snake"
    DEFAULT_SIZE = (320, 340)
    MEMORY_FOOTPRINT = 18

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.grid_size = 15
        self.snake = [(10, 10), (9, 10), (8, 10)]
        self.dir = (1, 0)
        self.food = (15, 10)
        self.timer = 0
        self.score = 0
        self.game_over = False

    def handle_event(self, event, local_mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self.dir != (0, 1): self.dir = (0, -1)
            elif event.key == pygame.K_DOWN and self.dir != (0, -1): self.dir = (0, 1)
            elif event.key == pygame.K_LEFT and self.dir != (1, 0): self.dir = (-1, 0)
            elif event.key == pygame.K_RIGHT and self.dir != (-1, 0): self.dir = (1, 0)
            elif event.key == pygame.K_r and self.game_over:
                self.__init__(self.os, self.window) # Reset

    def update(self):
        if self.game_over: return
        self.timer += 1
        if self.timer > 6: # Move speed
            self.timer = 0
            head = self.snake[0]
            new_head = (head[0] + self.dir[0], head[1] + self.dir[1])

            # Collisions
            if (new_head in self.snake or 
                new_head[0] < 0 or new_head[0] >= 20 or 
                new_head[1] < 0 or new_head[1] >= 20):
                self.game_over = True
                return

            self.snake.insert(0, new_head)
            if new_head == self.food:
                self.score += 10
                self.food = (random.randint(0, 19), random.randint(0, 19))
            else:
                self.snake.pop()

    def draw(self, surface):
        super().draw(surface)
        surface.blit(self.os.font_main.render(f"Score: {self.score}", True, THEME["accent"]), (10, 5))
        
        play_rect = pygame.Rect(10, 25, 300, 300)
        pygame.draw.rect(surface, (0, 0, 0), play_rect)
        pygame.draw.rect(surface, THEME["title_bar"], play_rect, 2)

        if self.game_over:
            text = self.os.font_bold.render("GAME OVER - Press 'R' to Restart", True, THEME["danger"])
            surface.blit(text, (30, 150))
            return

        # Draw Food
        fx, fy = 10 + self.food[0] * self.grid_size, 25 + self.food[1] * self.grid_size
        pygame.draw.rect(surface, THEME["danger"], (fx, fy, self.grid_size-1, self.grid_size-1))

        # Draw Snake
        for i, (sx, sy) in enumerate(self.snake):
            color = THEME["accent"] if i == 0 else THEME["title_bar_active"]
            px, py = 10 + sx * self.grid_size, 25 + sy * self.grid_size
            pygame.draw.rect(surface, color, (px, py, self.grid_size-1, self.grid_size-1))


# ==========================================
# WINDOW MANAGER & OS KERNEL
# ==========================================
class Window:
    def __init__(self, x, y, width, height, title, app_class, os_kernel):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.surface = pygame.Surface((width, height))
        self.app = app_class(os_kernel, self)
        
        self.title_rect = pygame.Rect(0, 0, width, 25)
        self.close_rect = pygame.Rect(width - 25, 0, 25, 25)

class AethelOS:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Aethel OS : Nexus")
        self.clock = pygame.time.Clock()

        self.font_main = pygame.font.SysFont("segoe ui, arial", 14)
        self.font_bold = pygame.font.SysFont("segoe ui, arial", 14, bold=True)
        self.font_mono = pygame.font.SysFont("consolas, monospace", 14)

        self.state = "BOOT"
        self.boot_timer = 0
        self.cpu_load = 0.0
        self.max_ram = 512
        
        self.windows = []
        self.active_window = None
        self.dragging_window = None
        self.drag_offset = (0, 0)

        # Expanded App Ecosystem
        self.desktop_icons = [
            {"name": "Terminal", "app": TerminalApp, "pos": (20, 20)},
            {"name": "Task Mgr", "app": TaskManagerApp, "pos": (20, 100)},
            {"name": "CodePad", "app": CodeEditorApp, "pos": (20, 180)},
            {"name": "Browser", "app": BrowserApp, "pos": (100, 20)},
            {"name": "Snake", "app": SnakeApp, "pos": (100, 100)}
        ]

    def get_ram_usage(self):
        return 32 + sum(win.app.MEMORY_FOOTPRINT for win in self.windows)

    def launch_app(self, app_class):
        offset = (len(self.windows) * 30) % 200
        w, h = app_class.DEFAULT_SIZE
        new_win = Window(180 + offset, 50 + offset, w, h, app_class.NAME, app_class, self)
        self.windows.append(new_win)
        self.active_window = new_win

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "DESKTOP":
                self.handle_desktop_events(event)

    def handle_desktop_events(self, event):
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_window = None
            for win in reversed(self.windows):
                if win.rect.collidepoint(mouse_pos):
                    clicked_window = win
                    break
            
            if clicked_window:
                self.windows.remove(clicked_window)
                self.windows.append(clicked_window)
                self.active_window = clicked_window

                local_x = mouse_pos[0] - win.rect.x
                local_y = mouse_pos[1] - win.rect.y

                if win.close_rect.collidepoint(local_x, local_y):
                    self.windows.remove(win)
                    self.active_window = self.windows[-1] if self.windows else None
                    return
                
                if win.title_rect.collidepoint(local_x, local_y):
                    self.dragging_window = win
                    self.drag_offset = (local_x, local_y)
                    return
            else:
                self.active_window = None

            if not clicked_window:
                for icon in self.desktop_icons:
                    icon_rect = pygame.Rect(icon["pos"][0], icon["pos"][1], 60, 60)
                    if icon_rect.collidepoint(mouse_pos):
                        self.launch_app(icon["app"])
                        return

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_window = None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_window:
                self.dragging_window.rect.x = mouse_pos[0] - self.drag_offset[0]
                self.dragging_window.rect.y = mouse_pos[1] - self.drag_offset[1]

        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN] and self.active_window:
            local_pos = (mouse_pos[0] - self.active_window.rect.x, mouse_pos[1] - self.active_window.rect.y)
            self.active_window.app.handle_event(event, local_pos)

    def draw_desktop_icons(self):
        for icon in self.desktop_icons:
            rect = pygame.Rect(icon["pos"][0], icon["pos"][1], 60, 60)
            pygame.draw.rect(self.screen, THEME["title_bar"], rect, border_radius=8)
            pygame.draw.rect(self.screen, THEME["accent"], rect, 2, border_radius=8)
            
            text = self.font_main.render(icon["name"], True, THEME["text_main"])
            text_rect = text.get_rect(centerx=rect.centerx, top=rect.bottom + 5)
            self.screen.blit(text, text_rect)

    def run(self):
        while True:
            # FRAME TIMING START
            frame_start = time.perf_counter()
            self.handle_events()
            
            # Update State
            if self.state == "BOOT":
                self.boot_timer += 1
                if self.boot_timer > 100: self.state = "DESKTOP"
            elif self.state == "DESKTOP":
                # Precise App Load Measuring
                for win in self.windows:
                    app_start = time.perf_counter()
                    win.app.update()
                    win.app.draw(win.surface)
                    app_time = time.perf_counter() - app_start
                    
                    # Convert app execution time into CPU% (assumes 60 FPS target = 0.0166s per frame)
                    load_pct = (app_time / 0.0166) * 100.0
                    win.app.load = (win.app.load * 0.9) + (load_pct * 0.1) # Smooth out values

            # Draw Layer
            self.screen.fill(THEME["desktop_bg"])
            if self.state == "BOOT":
                self.screen.blit(self.font_mono.render("Initializing OS Kernel...", True, THEME["accent"]), (20, 20))
            elif self.state == "DESKTOP":
                self.draw_desktop_icons()
                for win in self.windows:
                    is_active = (win == self.active_window)
                    title_color = THEME["title_bar_active"] if is_active else THEME["title_bar"]
                    
                    pygame.draw.rect(win.surface, title_color, win.title_rect)
                    win.surface.blit(self.font_bold.render(win.title, True, THEME["text_dark"] if is_active else THEME["text_main"]), (10, 3))
                    
                    pygame.draw.rect(win.surface, THEME["danger"], win.close_rect)
                    pygame.draw.line(win.surface, THEME["text_main"], (win.close_rect.left + 8, 8), (win.close_rect.right - 8, 17), 2)
                    pygame.draw.line(win.surface, THEME["text_main"], (win.close_rect.left + 8, 17), (win.close_rect.right - 8, 8), 2)
                    
                    pygame.draw.rect(win.surface, THEME["accent"] if is_active else THEME["title_bar"], (0, 0, win.rect.width, win.rect.height), 1)
                    self.screen.blit(win.surface, win.rect.topleft)

                # Taskbar
                taskbar_rect = pygame.Rect(0, SCREEN_HEIGHT - TASKBAR_HEIGHT, SCREEN_WIDTH, TASKBAR_HEIGHT)
                pygame.draw.rect(self.screen, THEME["taskbar_bg"], taskbar_rect)
                pygame.draw.line(self.screen, THEME["accent"], taskbar_rect.topleft, taskbar_rect.topright, 2)
                self.screen.blit(self.font_main.render(datetime.now().strftime("%H:%M"), True, THEME["text_main"]), (SCREEN_WIDTH - 60, SCREEN_HEIGHT - TASKBAR_HEIGHT + 10))

            pygame.display.flip()
            
            # FRAME TIMING END & OS LOAD CALC
            frame_time = time.perf_counter() - frame_start
            sys_load = (frame_time / 0.0166) * 100.0
            self.cpu_load = (self.cpu_load * 0.8) + (min(100.0, sys_load) * 0.2)
            self.clock.tick(60)

if __name__ == "__main__":
    os = AethelOS()
    os.run()
