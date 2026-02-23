import pygame
import sys
import time
import random
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
    "danger": (255, 65, 85)           # Red for close buttons
}

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
TASKBAR_HEIGHT = 40

# ==========================================
# MODULAR CPU ARCHITECTURE
# ==========================================
class Memory:
    """Modular Memory Unit (RAM/ROM)"""
    def __init__(self, size):
        self.data = [0] * size
    
    def read(self, addr):
        return self.data[addr % len(self.data)]
    
    def write(self, addr, val):
        self.data[addr % len(self.data)] = val & 0xFF

class ALU:
    """Modular Arithmetic Logic Unit"""
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
        self.regs = [0] * 8 # Expanded to 8 registers
        self.pc = 0
        self.rom = rom_data
        self.ram = Memory(256)
        self.ports = [0] * 256
        self.screen = [[0]*32 for _ in range(32)]
        
        # Pipeline Storage
        self.pipeline = {"F": None, "D": None, "E": None, "W": None}
        self.active_wires = []
        self.alu = ALU()

    def resolve(self, op):
        """Resolves if an operand is a Register or Literal."""
        if isinstance(op, str) and op.startswith("R"):
            # Data Forwarding logic
            if self.pipeline["W"] and self.pipeline["W"][1] == op:
                return self.pipeline["W"][0]
            return self.regs[int(op[1:])]
        return int(op) if op is not None else 0

    def tick(self):
        self.active_wires = []
        
        # 1. WRITEBACK
        if self.pipeline["W"]:
            val, target = self.pipeline["W"]
            if isinstance(target, str) and target.startswith("R"):
                self.regs[int(target[1:])] = val
                self.active_wires.append("WRITEBACK")

        # 2. EXECUTE
        self.pipeline["W"] = None
        if self.pipeline["E"]:
            op, dest, arg1, arg2 = self.pipeline["E"]
            v1, v2 = self.resolve(arg1), self.resolve(arg2)
            self.active_wires.append("REG_TO_ALU")

            if op == "OUT":
                port = self.resolve(dest)
                self.ports[port % 256] = v1
                
                # Hardware Mappings
                if port == 0: # PORT 0: Read Core ID
                    self.pipeline["W"] = (self.core_id, dest)
                if port == 12: 
                    self.screen[self.ports[11]%32][self.ports[10]%32] = 1
                if port == 13: 
                    self.screen = [[0]*32 for _ in range(32)]
                self.active_wires.append("ALU_TO_SCREEN")
            
            elif op == "JMP":
                self.pc = v2
                self.pipeline["F"] = self.pipeline["D"] = None
            
            elif op == "BEQ":
                if self.resolve(dest) == v1:
                    self.pc = v2
                    self.pipeline["F"] = self.pipeline["D"] = None
            else:
                # Use the Modular ALU
                result = self.alu.execute(op, v1, v2)
                self.pipeline["W"] = (result, dest)
                self.active_wires.append("ALU_TO_W")

        # 3. PIPELINE MOVE
        self.pipeline["E"] = self.pipeline["D"]
        self.pipeline["D"] = self.pipeline["F"]

        # 4. FETCH
        if self.pc < len(self.rom) and self.rom[self.pc]:
            self.pipeline["F"] = self.rom[self.pc]
            self.pc += 1
            self.active_wires.append("FETCH")
        else:
            self.pipeline["F"] = None

# ==========================================
# APPLICATION BASE CLASS
# ==========================================
class Application:
    """Base class for all Aethel OS apps."""
    NAME = "Unknown App"
    DEFAULT_SIZE = (400, 300)

    def __init__(self, os_kernel, window):
        self.os = os_kernel
        self.window = window

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
            "Type 'help' for available commands.",
            ""
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
            self.scrollback.append("PID  WINDOW TITLE")
            for i, win in enumerate(self.os.windows):
                self.scrollback.append(f"{i:<4} {win.title}")
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

class SysMonApp(Application):
    NAME = "System Monitor"
    DEFAULT_SIZE = (350, 200)
    MEMORY_FOOTPRINT = 8

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_main
        self.history = [0.0] * 50
        self.tick = 0

    def update(self):
        self.tick += 1
        if self.tick % 5 == 0:
            # Grab the REAL frame load from the OS Kernel
            usage = self.os.cpu_load
            self.history.pop(0)
            self.history.append(usage)

    def draw(self, surface):
        super().draw(surface)
        w, h = surface.get_size()
        
        surface.blit(self.font.render("Real-Time CPU Usage", True, THEME["accent"]), (10, 10))

        # Draw Graph Background
        graph_rect = pygame.Rect(10, 35, w - 20, 100)
        pygame.draw.rect(surface, (10, 10, 15), graph_rect)
        pygame.draw.rect(surface, THEME["title_bar"], graph_rect, 2)

        # Dynamic Scaling: scale the graph so small loads are still visible,
        # but big spikes don't go out of bounds.
        max_val = max(5.0, max(self.history)) 

        points = []
        step_x = graph_rect.width / max(1, len(self.history) - 1)
        for i, val in enumerate(self.history):
            x = graph_rect.left + (i * step_x)
            # Calculate Y based on our dynamic max_val
            y = graph_rect.bottom - (val / max_val * graph_rect.height)
            points.append((x, y))
        
        if len(points) > 1:
            pygame.draw.lines(surface, THEME["accent"], False, points, 2)

        # Bottom Stats Text
        current_load = self.history[-1]
        ram_usage = self.os.get_ram_usage()
        
        stat_text = self.font.render(f"Load: {current_load:.1f}% | RAM: {ram_usage}/{self.os.max_ram} MB", True, THEME["text_main"])
        tasks_text = self.font.render(f"Active Tasks: {len(self.os.windows)}", True, THEME["text_main"])
        
        surface.blit(stat_text, (10, 145))
        surface.blit(tasks_text, (10, 165))

class VmApp(Application):
    NAME = "Nexus VM Emulator"
    DEFAULT_SIZE = (600, 360)
    MEMORY_FOOTPRINT = 64

    # A custom Assembly Program that calculates physics to bounce a pixel around the screen!
    BOUNCING_PIXEL_ROM = [
        ("ADD", "R0", 0, 0),      # 0: X = 0
        ("ADD", "R1", 1, 0),      # 1: dx = 1
        ("ADD", "R2", 31, 0),     # 2: Max bounds = 31
        ("ADD", "R3", 0, 0),      # 3: Y = 0
        ("ADD", "R4", 1, 0),      # 4: dy = 1
        
        # --- LOOP START (5) ---
        ("OUT", 13, 0, 0),        # 5: Port 13: Clear screen
        ("OUT", 10, "R0", 0),     # 6: Port 10: Set X
        ("OUT", 11, "R3", 0),     # 7: Port 11: Set Y
        ("OUT", 12, 1, 0),        # 8: Port 12: Draw Pixel
        
        ("ADD", "R0", "R0", "R1"),# 9: X += dx
        ("ADD", "R3", "R3", "R4"),# 10: Y += dy
        
        # --- X BOUNCE LOGIC ---
        ("BEQ", "R0", "R2", 14),  # 11: If X == 31, Jump to Invert X
        ("BEQ", "R0", 0, 14),     # 12: If X == 0, Jump to Invert X
        ("JMP", 0, 0, 16),        # 13: Skip to Y check
        ("SUB", "R1", 0, "R1"),   # 14: dx = 0 - dx (Invert direction)
        ("JMP", 0, 0, 16),        # 15: Skip to Y check
        
        # --- Y BOUNCE LOGIC ---
        ("BEQ", "R3", "R2", 19),  # 16: If Y == 31, Jump to Invert Y
        ("BEQ", "R3", 0, 19),     # 17: If Y == 0, Jump to Invert Y
        ("JMP", 0, 0, 5),         # 18: Loop back to start
        ("SUB", "R4", 0, "R4"),   # 19: dy = 0 - dy (Invert direction)
        ("JMP", 0, 0, 5),         # 20: Loop back to start
    ]

    def __init__(self, os_kernel, window):
        super().__init__(os_kernel, window)
        self.font = os_kernel.font_mono
        self.cpu = ModularCPU(self.BOUNCING_PIXEL_ROM)
        self.running = True

    def handle_event(self, event, local_mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            btn_rect = pygame.Rect(400, 280, 160, 30)
            if btn_rect.collidepoint(local_mouse_pos):
                self.running = not self.running

    def update(self):
        if self.running:
            # Emulate multiple ticks per frame to speed up the virtual CPU
            for _ in range(4): 
                self.cpu.tick()

    def draw(self, surface):
        super().draw(surface)
        
        # Section 1: ROM Viewer (Left)
        pygame.draw.rect(surface, (15, 18, 22), (10, 10, 240, 330))
        surface.blit(self.font.render("ROM MEMORY", True, THEME["accent"]), (15, 15))
        
        y_offset = 35
        # Scroll the view so the active PC is always visible
        start_idx = max(0, self.cpu.pc - 6)
        for i in range(start_idx, min(len(self.cpu.rom), start_idx + 14)):
            color = THEME["accent"] if i == self.cpu.pc else THEME["text_main"]
            bg_color = (40, 50, 60) if i == self.cpu.pc else None
            
            inst = self.cpu.rom[i]
            text = f"{i:02d}: {inst[0]} {inst[1]} {inst[2]} {inst[3]}"
            
            if bg_color:
                pygame.draw.rect(surface, bg_color, (15, y_offset, 230, 20))
            surface.blit(self.font.render(text, True, color), (20, y_offset + 2))
            y_offset += 20

        # Section 2: CPU State (Middle)
        surface.blit(self.font.render("REGISTERS", True, THEME["accent"]), (270, 15))
        for i in range(5):
            val = self.cpu.regs[i]
            # Convert 2's complement negative numbers for display
            disp_val = val if val <= 127 else val - 256 
            text = f"R{i}: {val:03} ({disp_val})"
            surface.blit(self.font.render(text, True, THEME["text_main"]), (270, 35 + (i * 20)))

        surface.blit(self.font.render("PIPELINE", True, THEME["accent"]), (270, 160))
        stages = ["F", "D", "E", "W"]
        for i, stage in enumerate(stages):
            data = self.cpu.pipeline[stage]
            op_text = data[0] if data else "NOP"
            text = f"[{stage}]: {op_text}"
            surface.blit(self.font.render(text, True, THEME["text_main"]), (270, 180 + (i * 20)))

        # Section 3: Hardware Screen (Right)
        surface.blit(self.font.render("HW DISPLAY (PORT 12)", True, THEME["accent"]), (400, 15))
        
        screen_rect = pygame.Rect(400, 35, 160, 160)
        pygame.draw.rect(surface, (0, 0, 0), screen_rect)
        pygame.draw.rect(surface, THEME["title_bar"], screen_rect, 2)
        
        # Render the 32x32 CPU screen (5x5 pixels each to scale up to 160x160)
        for y in range(32):
            for x in range(32):
                if self.cpu.screen[y][x]:
                    pygame.draw.rect(surface, THEME["accent"], (400 + (x * 5), 35 + (y * 5), 5, 5))

        # Control Button
        btn_rect = pygame.Rect(400, 280, 160, 30)
        pygame.draw.rect(surface, THEME["title_bar"], btn_rect)
        pygame.draw.rect(surface, THEME["accent"], btn_rect, 1)
        btn_text = "PAUSE VM" if self.running else "RESUME VM"
        btn_surf = self.font.render(btn_text, True, THEME["accent"])
        surface.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width()//2, btn_rect.centery - 7))


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

        # Fonts
        self.font_main = pygame.font.SysFont("segoe ui, arial", 14)
        self.font_bold = pygame.font.SysFont("segoe ui, arial", 14, bold=True)
        self.font_mono = pygame.font.SysFont("consolas, monospace", 14)

        # State
        self.state = "BOOT"
        self.boot_timer = 0
        self.cpu_load = 0.0
        self.max_ram = 512
        
        # Window Management
        self.windows = []
        self.active_window = None
        self.dragging_window = None
        self.drag_offset = (0, 0)

        # Desktop Icons
        self.desktop_icons = [
            {"name": "Terminal", "app": TerminalApp, "rect": pygame.Rect(20, 20, 60, 60)},
            {"name": "Sys Monitor", "app": SysMonApp, "rect": pygame.Rect(20, 100, 60, 60)},
            {"name": "Nexus VM", "app": VmApp, "rect": pygame.Rect(20, 180, 60, 60)}
        ]

    def get_ram_usage(self):
        """Calculates total RAM used by OS and Apps."""
        usage = 32 # Base OS overhead
        for win in self.windows:
            usage += getattr(win.app, 'MEMORY_FOOTPRINT', 10)
        return usage

    def launch_app(self, app_class):
        offset = len(self.windows) * 25
        w, h = app_class.DEFAULT_SIZE
        new_win = Window(100 + offset, 100 + offset, w, h, app_class.NAME, app_class, self)
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
                    if icon["rect"].collidepoint(mouse_pos):
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

    def update(self):
        if self.state == "BOOT":
            self.boot_timer += 1
            if self.boot_timer > 120: 
                self.state = "DESKTOP"
        
        elif self.state == "DESKTOP":
            for win in self.windows:
                win.app.update()

    def draw(self):
        self.screen.fill(THEME["desktop_bg"])

        if self.state == "BOOT":
            self.screen.blit(self.font_mono.render("Initializing Aethel OS Kernel...", True, THEME["accent"]), (20, 20))
            if self.boot_timer > 40:
                self.screen.blit(self.font_mono.render("Loading Window Manager [OK]", True, THEME["text_main"]), (20, 45))
            if self.boot_timer > 80:
                self.screen.blit(self.font_mono.render("Mounting Virtual FS [OK]", True, THEME["text_main"]), (20, 70))

        elif self.state == "DESKTOP":
            self.draw_desktop_icons()
            self.draw_windows()
            self.draw_taskbar()

        pygame.display.flip()

    def draw_desktop_icons(self):
        for icon in self.desktop_icons:
            pygame.draw.rect(self.screen, THEME["title_bar"], icon["rect"], border_radius=8)
            pygame.draw.rect(self.screen, THEME["accent"], icon["rect"], 2, border_radius=8)
            
            text = self.font_main.render(icon["name"], True, THEME["text_main"])
            text_rect = text.get_rect(centerx=icon["rect"].centerx, top=icon["rect"].bottom + 5)
            self.screen.blit(text, text_rect)

    def draw_windows(self):
        for win in self.windows:
            is_active = (win == self.active_window)
            
            win.app.draw(win.surface)
            
            title_color = THEME["title_bar_active"] if is_active else THEME["title_bar"]
            text_color = THEME["text_dark"] if is_active else THEME["text_main"]
            
            pygame.draw.rect(win.surface, title_color, win.title_rect)
            win.surface.blit(self.font_bold.render(win.title, True, text_color), (10, 3))

            pygame.draw.rect(win.surface, THEME["danger"], win.close_rect)
            pygame.draw.line(win.surface, THEME["text_main"], (win.close_rect.left + 8, 8), (win.close_rect.right - 8, 17), 2)
            pygame.draw.line(win.surface, THEME["text_main"], (win.close_rect.left + 8, 17), (win.close_rect.right - 8, 8), 2)

            border_color = THEME["accent"] if is_active else THEME["title_bar"]
            pygame.draw.rect(win.surface, border_color, (0, 0, win.rect.width, win.rect.height), 1)

            self.screen.blit(win.surface, win.rect.topleft)

    def draw_taskbar(self):
        taskbar_rect = pygame.Rect(0, SCREEN_HEIGHT - TASKBAR_HEIGHT, SCREEN_WIDTH, TASKBAR_HEIGHT)
        pygame.draw.rect(self.screen, THEME["taskbar_bg"], taskbar_rect)
        pygame.draw.line(self.screen, THEME["accent"], taskbar_rect.topleft, taskbar_rect.topright, 2)

        start_rect = pygame.Rect(10, SCREEN_HEIGHT - TASKBAR_HEIGHT + 5, 80, 30)
        pygame.draw.rect(self.screen, THEME["accent"], start_rect, border_radius=4)
        self.screen.blit(self.font_bold.render("NEXUS", True, THEME["text_dark"]), (25, SCREEN_HEIGHT - TASKBAR_HEIGHT + 10))

        time_str = datetime.now().strftime("%H:%M")
        self.screen.blit(self.font_main.render(time_str, True, THEME["text_main"]), (SCREEN_WIDTH - 60, SCREEN_HEIGHT - TASKBAR_HEIGHT + 10))

    def run(self):
        while True:
            # 1. Mark the start time of the frame
            start_time = time.perf_counter()
            
            self.handle_events()
            self.update()
            self.draw()
            
            # 2. Mark the end time of computation (before we sleep/tick)
            work_time = time.perf_counter() - start_time
            
            # 3. Calculate load: 60 FPS means we have 0.01666 seconds per frame.
            # How much of that time did we spend doing actual work?
            target_frame_time = 1.0 / 60.0 
            load = (work_time / target_frame_time) * 100.0
            
            # Smooth it out slightly so the graph isn't complete static noise
            self.cpu_load = (self.cpu_load * 0.8) + (min(100.0, load) * 0.2)
            
            self.clock.tick(60)

if __name__ == "__main__":
    os = AethelOS()
    os.run()
