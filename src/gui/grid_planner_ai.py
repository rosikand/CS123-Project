import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import requests
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import threading

class CellType(Enum):
    EMPTY = "empty"
    PUPPER = "pupper"
    OBSTACLE = "obstacle"
    TARGET = "target"

class Orientation(Enum):
    NORTH = "↑"
    EAST = "→"
    SOUTH = "↓"
    WEST = "←"

@dataclass
class GridState:
    pupper_pos: Optional[tuple] = None
    pupper_orientation: Orientation = Orientation.NORTH
    obstacles: set = None
    target_pos: Optional[tuple] = None
    
    def __post_init__(self):
        if self.obstacles is None:
            self.obstacles = set()

class ClaudeAPI:
    def __init__(self):
        self.api_key = "" # API key should be set using the set_api_key method
        self.base_url = "https://api.anthropic.com/v1/messages"
        
    def set_api_key(self, api_key: str):
        self.api_key = api_key
        
    def generate_path(self, grid_representation: str, pupper_pos: tuple, pupper_orientation: str, target_pos: tuple, obstacles: List[tuple]) -> str:
        if not self.api_key:
            raise ValueError("API key not set")
            
        # Convert orientation to clear direction
        orientation_map = {
            "NORTH": "North",
            "EAST": "East", 
            "SOUTH": "South",
            "WEST": "West"
        }
        clear_orientation = orientation_map.get(pupper_orientation, pupper_orientation)
            
        prompt = f"""You are a pathfinding AI for a robot dog (pupper) on a 4x4 grid.

COORDINATE SYSTEM:
- Grid is 4x4 (rows 0-3, columns 0-3)
- (0,0) is TOP-LEFT corner
- (0,3) is TOP-RIGHT corner  
- (3,0) is BOTTOM-LEFT corner
- (3,3) is BOTTOM-RIGHT corner
- Position format: (row, col)

MOVEMENT RULES:
- North: row decreases (move up toward row 0)
- South: row increases (move down toward row 3)  
- East: column increases (move right toward col 3)
- West: column decreases (move left toward col 0)

CURRENT SITUATION:
- Pupper position: {pupper_pos} (row, col)
- Pupper facing: {clear_orientation}
- Target position: {target_pos} (row, col)
- Obstacle positions: {obstacles} ⚠️ CANNOT MOVE TO THESE!

Grid representation:
{grid_representation}

Legend: 
- . = empty cell (safe to move)
- X = obstacle (BLOCKED - cannot move here!)
- T = target destination
- N/E/S/W = pupper facing North/East/South/West

AVAILABLE COMMANDS:
- pupper.move(): Move one cell forward in current facing direction
- pupper.left(): Turn 90° counter-clockwise
- pupper.right(): Turn 90° clockwise

DIRECTIONS AND TURNING - CRITICAL INFORMATION:

Directional compass showing all turns:
      N
      |
 W ---|--- E
      |
      S

1. COUNTER-CLOCKWISE TURNS (pupper.left()):
   - North → West
   - West → South
   - South → East
   - East → North

2. CLOCKWISE TURNS (pupper.right()):
   - North → East
   - East → South
   - South → West
   - West → North

3. 180° TURNS (two options):
   - Option A: pupper.left() + pupper.left()
   - Option B: pupper.right() + pupper.right()
   - Examples: 
     - North → South: Use TWO lefts OR TWO rights
     - East → West: Use TWO lefts OR TWO rights

TURNING EXAMPLES - ANALYZE THESE CAREFULLY:
- If facing West and need to turn South: Use pupper.left() (West → South is counter-clockwise)
- If facing South and need to turn West: Use pupper.right() (South → West is clockwise)
- If facing East and need to turn West: Use pupper.left() + pupper.left() (180° turn)

CRITICAL: Before each pupper.move(), verify the destination cell is NOT in {obstacles}!

MOVEMENT VALIDATION EXAMPLES:
- If at (0,0) facing East, pupper.move() goes to (0,1)
  ✓ Check: Is (0,1) in obstacles list? If YES, DO NOT USE pupper.move()!
- If at (2,1) facing North, pupper.move() goes to (1,1)  
  ✓ Check: Is (1,1) in obstacles list? If YES, DO NOT USE pupper.move()!

STEP-BY-STEP APPROACH:
1. Analyze current position and facing direction
2. For each potential move, calculate destination coordinates
3. Check if destination is in obstacles list {obstacles}
4. If destination has obstacle, turn instead of moving
5. Find path that avoids ALL obstacles
6. ALWAYS use the shortest path possible

INSTRUCTIONS:
First, think through the problem step by step. Analyze the current situation, plan your path, and work through each move carefully. Check each potential destination against the obstacles list.

Then, at the very end of your response, provide the final commands after the marker "COMMANDS:" - one command per line, with no explanations.

Generate the shortest sequence of commands to reach {target_pos} while avoiding obstacles {obstacles}."""

        # Debug: Print the complete prompt
        print("=== FULL PROMPT BEING SENT TO AI ===")
        print(prompt)
        print("=== END OF PROMPT ===")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            full_response = result["content"][0]["text"].strip()
            
            # Debug: Print the complete response from Claude
            print("=== FULL CLAUDE API RESPONSE (UNFILTERED) ===")
            print(full_response)
            print("=== END OF FULL RESPONSE ===\n")
            
            # Parse out just the commands section
            if "COMMANDS:" in full_response:
                commands_section = full_response.split("COMMANDS:")[1].strip()
                print("=== EXTRACTED COMMANDS SECTION ===")
                print(commands_section)
                print("=== END OF COMMANDS SECTION ===\n")
                return commands_section
            else:
                # Fallback - return full response if no COMMANDS: marker found
                print("=== WARNING: NO COMMANDS MARKER FOUND, RETURNING FULL RESPONSE ===\n")
                return full_response
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid API response format: {str(e)}")

class GridPlannerAI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pupper Grid Planner with AI Pathfinding")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        self.grid_size = 4
        self.cell_size = 80
        self.state = GridState()
        self.current_tool = "pupper"
        self.claude_api = ClaudeAPI()
        self.path_commands = []
        
        self.setup_ui()
        self.create_grid()
        
    def setup_ui(self):
        # Main container with scrollable frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Pupper Grid Planner with AI Pathfinding", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Left panel - Tools
        tools_frame = ttk.LabelFrame(main_frame, text="Tools", padding="5")
        tools_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        
        # Tool selection
        self.tool_var = tk.StringVar(value="pupper")
        
        ttk.Radiobutton(tools_frame, text="Place Pupper", variable=self.tool_var, 
                       value="pupper", command=self.update_tool).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(tools_frame, text="Place Obstacle", variable=self.tool_var, 
                       value="obstacle", command=self.update_tool).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(tools_frame, text="Set Target", variable=self.tool_var, 
                       value="target", command=self.update_tool).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(tools_frame, text="Clear Cell", variable=self.tool_var, 
                       value="clear", command=self.update_tool).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Orientation frame
        orientation_frame = ttk.LabelFrame(tools_frame, text="Pupper Orientation", padding="5")
        orientation_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.orientation_var = tk.StringVar(value="NORTH")
        orientations = [("North ↑", "NORTH"), ("East →", "EAST"), 
                       ("South ↓", "SOUTH"), ("West ←", "WEST")]
        
        for i, (text, value) in enumerate(orientations):
            ttk.Radiobutton(orientation_frame, text=text, variable=self.orientation_var, 
                           value=value, command=self.update_orientation).grid(row=i//2, column=i%2, sticky=tk.W, padx=5, pady=2)
        
        # Action buttons
        button_frame = ttk.Frame(tools_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).grid(row=0, column=0, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(button_frame, text="Export Grid", command=self.export_grid).grid(row=1, column=0, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(button_frame, text="Import Grid", command=self.import_grid).grid(row=2, column=0, pady=2, sticky=(tk.W, tk.E))
        
        # AI Controls
        ai_frame = ttk.LabelFrame(tools_frame, text="AI Pathfinding", padding="5")
        ai_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(ai_frame, text="Set API Key", command=self.set_api_key).grid(row=0, column=0, pady=2, sticky=(tk.W, tk.E))
        ttk.Button(ai_frame, text="Generate Path", command=self.generate_path).grid(row=1, column=0, pady=2, sticky=(tk.W, tk.E))
        
        # Grid frame
        self.grid_frame = ttk.LabelFrame(main_frame, text="4x4 Grid", padding="10")
        self.grid_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right panel - AI Output
        ai_output_frame = ttk.LabelFrame(main_frame, text="AI Generated Path", padding="5")
        ai_output_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Commands display
        commands_label = ttk.Label(ai_output_frame, text="Commands:")
        commands_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Create text widget with scrollbar for commands
        commands_frame = ttk.Frame(ai_output_frame)
        commands_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.commands_text = tk.Text(commands_frame, width=25, height=15, font=('Courier', 10))
        commands_scrollbar = ttk.Scrollbar(commands_frame, orient=tk.VERTICAL, command=self.commands_text.yview)
        self.commands_text.configure(yscrollcommand=commands_scrollbar.set)
        
        self.commands_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        commands_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        commands_frame.columnconfigure(0, weight=1)
        commands_frame.rowconfigure(0, weight=1)
        
        # Copy button
        ttk.Button(ai_output_frame, text="Copy Commands", command=self.copy_commands).grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Simulate button
        ttk.Button(ai_output_frame, text="Simulate Path", command=self.simulate_path).grid(row=3, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Configure AI output frame
        ai_output_frame.columnconfigure(0, weight=1)
        ai_output_frame.rowconfigure(1, weight=1)
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready - Place pupper and target, then generate path with AI")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
    def create_grid(self):
        self.grid_buttons = {}
        
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                btn = tk.Button(self.grid_frame, 
                              width=8, height=4,
                              font=('Arial', 12, 'bold'),
                              relief='raised',
                              borderwidth=2,
                              command=lambda r=row, c=col: self.cell_clicked(r, c))
                btn.grid(row=row, column=col, padx=1, pady=1)
                self.grid_buttons[(row, col)] = btn
                
        self.update_grid_display()
        
    def cell_clicked(self, row, col):
        pos = (row, col)
        
        if self.current_tool == "pupper":
            # Remove pupper from previous position
            if self.state.pupper_pos:
                old_pos = self.state.pupper_pos
                if old_pos in self.state.obstacles:
                    self.state.obstacles.remove(old_pos)
                    
            self.state.pupper_pos = pos
            # Remove obstacle or target from this position if present
            if pos in self.state.obstacles:
                self.state.obstacles.remove(pos)
            if self.state.target_pos == pos:
                self.state.target_pos = None
                
            self.status_label.config(text=f"Pupper placed at ({row}, {col})")
            
        elif self.current_tool == "obstacle":
            if pos == self.state.pupper_pos:
                self.status_label.config(text="Cannot place obstacle on pupper!")
                return
            if pos == self.state.target_pos:
                self.state.target_pos = None
                
            if pos in self.state.obstacles:
                self.state.obstacles.remove(pos)
                self.status_label.config(text=f"Obstacle removed from ({row}, {col})")
            else:
                self.state.obstacles.add(pos)
                self.status_label.config(text=f"Obstacle placed at ({row}, {col})")
                
        elif self.current_tool == "target":
            if pos == self.state.pupper_pos:
                self.status_label.config(text="Cannot set target on pupper!")
                return
            if pos in self.state.obstacles:
                self.state.obstacles.remove(pos)
                
            if self.state.target_pos == pos:
                self.state.target_pos = None
                self.status_label.config(text=f"Target removed from ({row}, {col})")
            else:
                self.state.target_pos = pos
                self.status_label.config(text=f"Target set at ({row}, {col})")
                
        elif self.current_tool == "clear":
            if pos == self.state.pupper_pos:
                self.state.pupper_pos = None
            if pos in self.state.obstacles:
                self.state.obstacles.remove(pos)
            if self.state.target_pos == pos:
                self.state.target_pos = None
            self.status_label.config(text=f"Cell ({row}, {col}) cleared")
            
        self.update_grid_display()
        # Clear previous path when grid changes
        self.clear_path_display()
        
    def update_grid_display(self):
        for (row, col), btn in self.grid_buttons.items():
            pos = (row, col)
            
            # Reset button style
            btn.config(bg='white', fg='black', text='')
            
            # Set content based on state
            if pos == self.state.pupper_pos:
                orientation_symbol = Orientation[self.orientation_var.get()].value
                btn.config(bg='#4CAF50', fg='black', text=f'🐕\n{orientation_symbol}')
            elif pos in self.state.obstacles:
                btn.config(bg='#F44336', fg='white', text='⬛')
            elif pos == self.state.target_pos:
                btn.config(bg='#FF9800', fg='white', text='🎯')
            else:
                btn.config(bg='#E8E8E8', fg='gray', text=f'{row},{col}')
                
    def update_tool(self):
        self.current_tool = self.tool_var.get()
        tool_names = {
            "pupper": "Place Pupper",
            "obstacle": "Place Obstacle", 
            "target": "Set Target",
            "clear": "Clear Cell"
        }
        self.status_label.config(text=f"Tool: {tool_names[self.current_tool]} - Click on grid to use")
        
    def update_orientation(self):
        self.state.pupper_orientation = Orientation[self.orientation_var.get()]
        self.update_grid_display()
        
        if self.state.pupper_pos:
            row, col = self.state.pupper_pos
            orientation_name = self.orientation_var.get().lower()
            self.status_label.config(text=f"Pupper orientation changed to {orientation_name} at ({row}, {col})")
        
    def clear_all(self):
        if messagebox.askyesno("Clear All", "Are you sure you want to clear the entire grid?"):
            self.state = GridState()
            self.update_grid_display()
            self.clear_path_display()
            self.status_label.config(text="Grid cleared")
            
    def set_api_key(self):
        api_key = simpledialog.askstring("Claude API Key", 
                                       "Enter your Claude API key:", 
                                       show='*')
        if api_key:
            self.claude_api.set_api_key(api_key.strip())
            self.status_label.config(text="API key set successfully")
        
    def generate_path(self):
        if not self.claude_api.api_key:
            messagebox.showerror("API Key Required", "Please set your Claude API key first")
            return
            
        if not self.state.pupper_pos:
            messagebox.showerror("Missing Pupper", "Please place the pupper on the grid first")
            return
            
        if not self.state.target_pos:
            messagebox.showerror("Missing Target", "Please set a target position first")
            return
            
        self.status_label.config(text="Generating path with AI...")
        self.root.update()
        
        # Run API call in separate thread to avoid blocking UI
        threading.Thread(target=self._generate_path_thread, daemon=True).start()
        
    def _generate_path_thread(self):
        try:
            grid_repr = self.get_grid_representation()
            orientation_name = self.orientation_var.get()
            
            # Debug: Print what we're sending to AI
            print("=== DEBUG: Sending to AI ===")
            print(f"Pupper position: {self.state.pupper_pos}")
            print(f"Pupper orientation: {orientation_name}")
            print(f"Target position: {self.state.target_pos}")
            print(f"Obstacles: {list(self.state.obstacles)}")
            print("Grid representation:")
            print(grid_repr)
            print("===========================")
            
            result = self.claude_api.generate_path(
                grid_repr, 
                self.state.pupper_pos, 
                orientation_name,
                self.state.target_pos, 
                list(self.state.obstacles)
            )
            
            print(f"AI Response: {result}")
            print("===========================")
            
            # Update UI in main thread
            self.root.after(0, self._update_path_result, result)
            
        except Exception as e:
            print(f"Error: {e}")
            self.root.after(0, self._show_error, f"Failed to generate path: {str(e)}")
            
    def _update_path_result(self, result):
        self.commands_text.delete(1.0, tk.END)
        self.commands_text.insert(tk.END, result)
        
        # Parse commands
        lines = result.strip().split('\n')
        self.path_commands = [line.strip() for line in lines if line.strip() and 'pupper.' in line]
        
        # Debug: Print the final parsed commands
        print("=== FINAL PARSED COMMANDS ===")
        print(self.path_commands)
        print("=== END OF PARSED COMMANDS ===\n")
        
        self.status_label.config(text=f"Path generated! {len(self.path_commands)} commands")
        
    def _show_error(self, error_msg):
        self.status_label.config(text="Path generation failed")
        messagebox.showerror("AI Error", error_msg)
        
    def copy_commands(self):
        commands = self.commands_text.get(1.0, tk.END).strip()
        if commands:
            self.root.clipboard_clear()
            self.root.clipboard_append(commands)
            self.status_label.config(text="Commands copied to clipboard")
        else:
            messagebox.showinfo("No Commands", "No commands to copy. Generate a path first.")
            
    def simulate_path(self):
        if not self.path_commands:
            messagebox.showinfo("No Path", "Generate a path first before simulating")
            return
            
        # Create simulation window
        self.show_simulation()
        
    def show_simulation(self):
        sim_window = tk.Toplevel(self.root)
        sim_window.title("Path Simulation")
        sim_window.geometry("400x300")
        
        frame = ttk.Frame(sim_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Path Simulation", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # Commands list
        commands_frame = ttk.LabelFrame(frame, text="Commands Sequence", padding="5")
        commands_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        commands_listbox = tk.Listbox(commands_frame, font=('Courier', 10))
        scrollbar_sim = ttk.Scrollbar(commands_frame, orient=tk.VERTICAL, command=commands_listbox.yview)
        commands_listbox.configure(yscrollcommand=scrollbar_sim.set)
        
        for i, cmd in enumerate(self.path_commands):
            commands_listbox.insert(tk.END, f"{i+1:2d}. {cmd}")
            
        commands_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_sim.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary
        summary_text = f"""
Summary:
• Total commands: {len(self.path_commands)}
• Start: {self.state.pupper_pos}
• Target: {self.state.target_pos}
• Obstacles: {len(self.state.obstacles)}
        """
        
        ttk.Label(frame, text=summary_text, justify=tk.LEFT).pack()
        
    def clear_path_display(self):
        self.commands_text.delete(1.0, tk.END)
        self.path_commands = []
        
    def export_grid(self):
        try:
            # Create export data
            export_data = {
                "grid_size": self.grid_size,
                "pupper": {
                    "position": self.state.pupper_pos,
                    "orientation": self.state.pupper_orientation.name if self.state.pupper_pos else None
                },
                "obstacles": list(self.state.obstacles),
                "target": self.state.target_pos,
                "grid_representation": self.get_grid_representation(),
                "ai_commands": self.path_commands
            }
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.status_label.config(text=f"Grid exported to {filename}")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export grid: {str(e)}")
            
    def import_grid(self):
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                self.state = GridState()
                
                if data.get("pupper", {}).get("position"):
                    self.state.pupper_pos = tuple(data["pupper"]["position"])
                    if data["pupper"].get("orientation"):
                        self.state.pupper_orientation = Orientation[data["pupper"]["orientation"]]
                        self.orientation_var.set(data["pupper"]["orientation"])
                        
                self.state.obstacles = set(tuple(obs) for obs in data.get("obstacles", []))
                
                if data.get("target"):
                    self.state.target_pos = tuple(data["target"])
                    
                # Load AI commands if available
                if data.get("ai_commands"):
                    self.path_commands = data["ai_commands"]
                    commands_text = '\n'.join(self.path_commands)
                    self.commands_text.delete(1.0, tk.END)
                    self.commands_text.insert(tk.END, commands_text)
                    
                self.update_grid_display()
                self.status_label.config(text=f"Grid imported from {filename}")
                
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import grid: {str(e)}")
            
    def get_grid_representation(self):
        """Generate a text representation of the grid"""
        grid = [['.' for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        # Place obstacles
        for (row, col) in self.state.obstacles:
            grid[row][col] = 'X'
            
        # Place target
        if self.state.target_pos:
            row, col = self.state.target_pos
            grid[row][col] = 'T'
            
        # Place pupper (overwrites target if same position)
        if self.state.pupper_pos:
            row, col = self.state.pupper_pos
            orientation_map = {
                Orientation.NORTH: 'N',
                Orientation.EAST: 'E',
                Orientation.SOUTH: 'S',
                Orientation.WEST: 'W'
            }
            grid[row][col] = orientation_map[self.state.pupper_orientation]
            
        return '\n'.join(' '.join(row) for row in grid)

def main():
    root = tk.Tk()
    app = GridPlannerAI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 