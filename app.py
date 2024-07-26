import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import ctypes
from ctypes import windll

class CooldownTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("League of Legends Cooldown Tracker")
        self.champions = {}
        self.api_version = "14.14.1"  # Use the current version
        self.base_url = f"https://ddragon.leagueoflegends.com/cdn/{self.api_version}/data/en_US"
        self.valid_champions = self.get_valid_champions()
        self.setup_ui()

        # Set the window to be always on top and remove window decorations (optional)
        self.root.attributes('-topmost', True)  # Keep the window on top

        # Enable window dragging
        self.enable_dragging()

        # Enable window resizing
        self.enable_resizing()

    def enable_dragging(self):
        def start_drag(event):
            self.x = event.x
            self.y = event.y

        def on_drag(event):
            x = self.root.winfo_pointerx() - self.x
            y = self.root.winfo_pointery() - self.y
            self.root.geometry(f"+{x}+{y}")

        self.root.bind("<Button-1>", start_drag)
        self.root.bind("<B1-Motion>", on_drag)

    def enable_resizing(self):
        def start_resize(event):
            self.width = event.x
            self.height = event.y

        def on_resize(event):
            width = self.root.winfo_pointerx() - self.root.winfo_rootx()
            height = self.root.winfo_pointery() - self.root.winfo_rooty()
            self.root.geometry(f"{width}x{height}")

        self.resize_handle = ttk.Sizegrip(self.root)
        self.resize_handle.pack(side="right", anchor="se")
        self.resize_handle.bind("<Button-1>", start_resize)
        self.resize_handle.bind("<B1-Motion>", on_resize)

    def setup_ui(self):
        # Add champions section
        self.add_champion_frame = ttk.Frame(self.root)
        self.add_champion_frame.pack(pady=10)

        self.champion_name_label = ttk.Label(self.add_champion_frame, text="Name")
        self.champion_name_label.grid(row=0, column=0, padx=5)

        self.champion_entry = ttk.Entry(self.add_champion_frame, width=20)
        self.champion_entry.grid(row=0, column=1, padx=5)

        self.add_button = ttk.Button(self.add_champion_frame, text="Add Champion", command=self.add_champion)
        self.add_button.grid(row=0, column=2, padx=5)

        # Champions list section
        self.champions_frame = ttk.Frame(self.root)
        self.champions_frame.pack(pady=10, fill="x")

    def get_valid_champions(self):
        response = requests.get(f"{self.base_url}/champion.json")
        data = response.json()
        return list(data['data'].keys())

    def show_message(self, message):
        msg = tk.Toplevel()
        msg_label = ttk.Label(msg, text=message, padding=10)
        msg_label.pack()
        self.root.after(1000, msg.destroy)  # Close message box after 2 seconds

    def add_champion(self):
        champion_name = self.champion_entry.get().capitalize()

        if champion_name in self.champions:
            self.show_message("This champion already exists.")
            self.champion_entry.delete(0, tk.END)  # Clear the text box
            return
        if champion_name not in self.valid_champions:
            self.show_message("Invalid champion name.")
            self.champion_entry.delete(0, tk.END)  # Clear the text box
            return

        self.champions[champion_name] = {
            "ability_haste": tk.StringVar(value="0"),
            "abilities": {}
        }
        self.display_champion(champion_name)
        self.champion_entry.delete(0, tk.END)  # Clear the text box

    def display_champion(self, champion_name):
        frame = ttk.Frame(self.champions_frame)
        frame.pack(pady=5, fill="x")

        ttk.Label(frame, text=champion_name).pack(side="left", padx=5)

        abilities = self.get_champion_abilities(champion_name)
        for ability, cooldowns in abilities.items():
            icon = self.get_ability_icon(champion_name, ability)
            if icon:
                icon = icon.resize((30, 30), Image.LANCZOS)
                icon = ImageTk.PhotoImage(icon)

                # Create a frame for the ability icon and level controls
                ability_frame = ttk.Frame(frame)
                ability_frame.pack(side="left", padx=5, pady=2)

                icon_label = ttk.Label(ability_frame, image=icon)
                icon_label.image = icon
                icon_label.pack(side="top")

                # Check if the ability scales with level
                scales_with_level = len(cooldowns) > 1 and cooldowns[0] != cooldowns[1]

                level_var = tk.StringVar(value="1" if scales_with_level else "X")
                self.champions[champion_name]["abilities"][ability] = {
                    "cooldowns": cooldowns,
                    "level": level_var
                }

                level_frame = ttk.Frame(ability_frame)
                level_frame.pack(side="top")

                level_label = ttk.Label(level_frame, textvariable=level_var)
                level_label.pack(side="top", pady=2)

                minus_button = ttk.Button(level_frame, text="-", width=2)
                minus_button.pack(side="left")
                plus_button = ttk.Button(level_frame, text="+", width=2)
                plus_button.pack(side="left")

                if scales_with_level:
                    minus_button.configure(command=lambda ab=ability, lbl=icon_label, min_btn=minus_button, plus_btn=plus_button: self.update_ability_level(champion_name, ab, lbl, -1, min_btn, plus_btn))
                    plus_button.configure(command=lambda ab=ability, lbl=icon_label, min_btn=minus_button, plus_btn=plus_button: self.update_ability_level(champion_name, ab, lbl, 1, min_btn, plus_btn))
                else:
                    minus_button.state(['disabled'])
                    plus_button.state(['disabled'])

                # Fetch ability haste at the time of click
                icon_label.bind("<Button-1>",
                                lambda e, ab=ability, cd=cooldowns, champ=champion_name, lbl=icon_label: self.start_cooldown(ab, cd, champ, lbl))

        ability_haste_entry = ttk.Entry(frame, width=5, textvariable=self.champions[champion_name]["ability_haste"])
        ability_haste_entry.pack(side="left", padx=5)

    def get_champion_abilities(self, champion_name):
        response = requests.get(f"{self.base_url}/champion/{champion_name}.json")
        data = response.json()
        abilities = {}
        for spell in data['data'][champion_name]['spells']:
            abilities[spell['id']] = spell['cooldown']
        return abilities

    def get_ability_icon(self, champion_name, ability_name):
        response = requests.get(f"{self.base_url}/champion/{champion_name}.json")
        data = response.json()
        for spell in data['data'][champion_name]['spells']:
            if spell['id'] == ability_name:
                icon_url = f"https://ddragon.leagueoflegends.com/cdn/{self.api_version}/img/spell/{spell['id']}.png"
                icon_response = requests.get(icon_url)
                return Image.open(BytesIO(icon_response.content))
        return None

    def update_ability_level(self, champion_name, ability, icon_label, delta, minus_button, plus_button):
        current_level = int(self.champions[champion_name]["abilities"][ability]["level"].get())
        max_level = len(self.champions[champion_name]["abilities"][ability]["cooldowns"])
        new_level = current_level + delta

        if 1 <= new_level <= max_level:
            self.champions[champion_name]["abilities"][ability]["level"].set(new_level)

        # Update button states
        if new_level == 1:
            minus_button.state(['disabled'])
        else:
            minus_button.state(['!disabled'])

        if new_level == max_level:
            plus_button.state(['disabled'])
        else:
            plus_button.state(['!disabled'])

    def start_cooldown(self, ability, cooldowns, champion_name, icon_label):
        level_var = self.champions[champion_name]["abilities"][ability]["level"].get()
        ability_haste_str = self.champions[champion_name]["ability_haste"].get()

        # Ensure ability haste defaults to 0 if the field is empty
        ability_haste = int(ability_haste_str) if ability_haste_str.isdigit() else 0

        # If the ability has only one cooldown, always use the first cooldown value
        level = 1 if level_var == "X" else int(level_var)
        cooldown = cooldowns[level - 1] / (1 + ability_haste / 100)
        print(cooldown, ability_haste)

        # Create a semi-transparent overlay
        overlay = tk.Label(icon_label, bg="black", fg="white", width=icon_label.winfo_width(), height=icon_label.winfo_height())
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.config(font=("Helvetica", 10))

        def countdown(cooldown):
            if cooldown > 0:
                overlay.config(text=f"{cooldown:.1f}s")
                self.root.after(100, countdown, cooldown - 0.1)
            else:
                overlay.destroy()

        countdown(cooldown)

if __name__ == "__main__":
    root = tk.Tk()
    app = CooldownTracker(root)
    root.mainloop()
