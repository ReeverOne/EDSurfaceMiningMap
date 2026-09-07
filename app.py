import os
import math
import pandas as pd
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configure CustomTkinter Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CSV_FILE = "surfaceminingmap.csv"
COLUMNS = ["system", "planet", "mining_spot_number", "type", "rigs", "direction", "distance", "lat", "long"]

def initialize_csv():
    """Ensures the database file exists with appropriate headers."""
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(CSV_FILE, index=False)

def load_data():
    """Loads CSV data safely into a pandas DataFrame."""
    initialize_csv()
    try:
        df = pd.read_csv(CSV_FILE)
        df["mining_spot_number"] = df["mining_spot_number"].astype(str)
        df["rigs"] = df["rigs"].astype(str)
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return pd.DataFrame(columns=COLUMNS)

class MiningMapApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Elite Dangerous - Surface Mining Tracker")
        self.geometry("1150x750")

        self.df = load_data()

        # Navigation Bar
        self.nav_frame = ctk.CTkFrame(self, height=50)
        self.nav_frame.pack(fill="x", padx=10, pady=5)

        self.btn_display = ctk.CTkButton(self.nav_frame, text="Display Map", command=self.show_display_page)
        self.btn_display.pack(side="left", padx=10, pady=10)

        self.btn_input = ctk.CTkButton(self.nav_frame, text="Input Data", command=self.show_input_page)
        self.btn_input.pack(side="left", padx=10, pady=10)

        self.btn_manage = ctk.CTkButton(self.nav_frame, text="Manage Data", command=self.show_manage_page)
        self.btn_manage.pack(side="left", padx=10, pady=10)

        # Main Content Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=5)

        self.display_page = DisplayPage(self.container, self)
        self.input_page = InputPage(self.container, self)
        self.manage_page = ManagePage(self.container, self)

        self.show_display_page()

    def hide_all_pages(self):
        self.display_page.pack_forget()
        self.input_page.pack_forget()
        self.manage_page.pack_forget()

    def show_display_page(self):
        self.df = load_data()
        self.hide_all_pages()
        self.display_page.refresh_filters()
        self.display_page.pack(fill="both", expand=True)

    def show_input_page(self):
        self.df = load_data()
        self.hide_all_pages()
        self.input_page.refresh_dropdowns()
        self.input_page.pack(fill="both", expand=True)

    def show_manage_page(self):
        self.df = load_data()
        self.hide_all_pages()
        self.manage_page.load_table_data()
        self.manage_page.pack(fill="both", expand=True)


class DisplayPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.active_spot_df = pd.DataFrame()
        self.plotted_points = []  # Stores point details for interactive event handling

        # Left Control Panel (Filters)
        self.left_panel = ctk.CTkFrame(self, width=300)
        self.left_panel.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.left_panel, text="Location Selection", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(self.left_panel, text="System:").pack(anchor="w", padx=10)
        self.sys_var = ctk.StringVar(value="--Select--")
        self.sys_dropdown = ctk.CTkOptionMenu(self.left_panel, variable=self.sys_var, command=self.on_system_change)
        self.sys_dropdown.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.left_panel, text="Planet:").pack(anchor="w", padx=10)
        self.planet_var = ctk.StringVar(value="--Select--")
        self.planet_dropdown = ctk.CTkOptionMenu(self.left_panel, variable=self.planet_var, command=self.on_planet_change)
        self.planet_dropdown.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.left_panel, text="Mining Spot #:").pack(anchor="w", padx=10)
        self.spot_var = ctk.StringVar(value="--Select--")
        self.spot_dropdown = ctk.CTkOptionMenu(self.left_panel, variable=self.spot_var, command=self.update_map)
        self.spot_dropdown.pack(fill="x", padx=10, pady=5)

        ctk.CTkFrame(self.left_panel, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(self.left_panel, text="Map Filters", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(0, 5))

        self.type_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="Deposit Types", height=120)
        self.type_frame.pack(fill="x", padx=10, pady=5)
        self.type_vars = {}

        self.rig_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="Rigs Filter", height=120)
        self.rig_frame.pack(fill="x", padx=10, pady=5)
        self.rig_vars = {}

        # Status Bar for Clipboard Notification
        self.status_label = ctk.CTkLabel(self.left_panel, text="Click a point to copy Lat/Long", font=("Arial", 11, "italic"))
        self.status_label.pack(fill="x", padx=10, pady=(15, 5))

        # Right Map Canvas Area
        self.map_panel = ctk.CTkFrame(self)
        self.map_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.canvas_widget = None

    def refresh_filters(self):
        df = self.controller.df
        systems = sorted(df["system"].dropna().unique().tolist()) if not df.empty else []
        self.sys_dropdown.configure(values=["--Select--"] + systems)
        self.sys_var.set("--Select--")
        self.planet_dropdown.configure(values=["--Select--"])
        self.planet_var.set("--Select--")
        self.spot_dropdown.configure(values=["--Select--"])
        self.spot_var.set("--Select--")
        self.clear_checkboxes()

    def on_system_change(self, choice):
        if choice == "--Select--":
            return
        df = self.controller.df
        filtered = df[df["system"] == choice]
        planets = sorted(filtered["planet"].dropna().unique().tolist())
        self.planet_dropdown.configure(values=["--Select--"] + planets)
        self.planet_var.set("--Select--")
        self.spot_dropdown.configure(values=["--Select--"])
        self.spot_var.set("--Select--")

    def on_planet_change(self, choice):
        if choice == "--Select--":
            return
        df = self.controller.df
        filtered = df[(df["system"] == self.sys_var.get()) & (df["planet"] == choice)]
        spots = sorted(filtered["mining_spot_number"].dropna().unique().tolist())
        self.spot_dropdown.configure(values=["--Select--"] + spots)
        self.spot_var.set("--Select--")

    def clear_checkboxes(self):
        for widget in self.type_frame.winfo_children():
            widget.destroy()
        for widget in self.rig_frame.winfo_children():
            widget.destroy()
        self.type_vars.clear()
        self.rig_vars.clear()

    def plot_map(self):
        if self.canvas_widget:
            self.canvas_widget.destroy()

        if self.active_spot_df.empty:
            return

        self.plotted_points.clear()

        active_types = [t for t, var in self.type_vars.items() if var.get()]
        active_rigs = [r for r, var in self.rig_vars.items() if var.get()]

        filtered_data = self.active_spot_df[
            (self.active_spot_df["type"].isin(active_types)) &
            (self.active_spot_df["rigs"].isin(active_rigs))
        ]

        self.fig, self.ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(6, 6))
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#1e1e1e')

        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)

        self.ax.scatter(0, 0, color='red', s=120, label='Spot Center', zorder=5)

        BASE_RIG_AREA = 40

        unique_types = sorted(filtered_data["type"].unique()) if not filtered_data.empty else []
        cmap = plt.colormaps.get_cmap("tab10")
        type_color_map = {commodity: cmap(i % 10) for i, commodity in enumerate(unique_types)}

        plotted_types = set()

        for idx, row in filtered_data.iterrows():
            theta = math.radians(float(row["direction"]))
            r = float(row["distance"])
            commodity_type = str(row["type"])
            lat = row.get("lat", "N/A")
            long_val = row.get("long", "N/A")

            try:
                rig_count = max(1, int(row["rigs"]))
            except (ValueError, TypeError):
                rig_count = 1

            marker_size = BASE_RIG_AREA * rig_count
            point_color = type_color_map.get(commodity_type, "cyan")

            legend_label = commodity_type if commodity_type not in plotted_types else ""
            plotted_types.add(commodity_type)

            scatter_obj = self.ax.scatter(
                theta,
                r,
                s=marker_size,
                color=point_color,
                label=legend_label,
                alpha=0.8,
                edgecolors='white',
                linewidth=0.5,
                zorder=4
            )

            self.ax.annotate(f" {commodity_type} ({rig_count}R)", (theta, r), color='white', fontsize=8)

            # Store metadata for event listener matching
            self.plotted_points.append({
                "scatter": scatter_obj,
                "type": commodity_type,
                "rigs": rig_count,
                "lat": lat,
                "long": long_val
            })

        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='gray', linestyle='--', alpha=0.5)
        self.ax.set_title(f"Spot Map: {self.spot_var.get()} ({self.planet_var.get()})", color='white', pad=20)

        if plotted_types:
            legend = self.ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), facecolor='#2b2b2b', edgecolor='none')
            for text in legend.get_texts():
                text.set_color('white')

        # Create invisible annotation box for hover effects
        self.annot = self.ax.annotate(
            "",
            xy=(0,0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="#333333", ec="white", lw=1),
            color="white",
            fontsize=9
        )
        self.annot.set_visible(False)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_panel)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        # Bind Matplotlib interaction events
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas.mpl_connect("button_press_event", self.on_click)

        self.canvas.draw()

    def on_hover(self, event):
        """Displays tooltip box when hovering over a scatter point."""
        if event.inaxes != self.ax:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return

        found = False
        for pt_info in self.plotted_points:
            cont, ind = pt_info["scatter"].contains(event)
            if cont:
                pos = pt_info["scatter"].get_offsets()[ind["ind"][0]]
                self.annot.xy = pos
                text = f"{pt_info['type']} ({pt_info['rigs']} Rigs)\nLat: {pt_info['lat']}\nLong: {pt_info['long']}"
                self.annot.set_text(text)
                self.annot.set_visible(True)
                self.canvas.draw_idle()
                found = True
                break

        if not found and self.annot.get_visible():
            self.annot.set_visible(False)
            self.canvas.draw_idle()

    def on_click(self, event):
        """Copies lat/long coordinates to the system clipboard on point click."""
        if event.inaxes != self.ax:
            return

        for pt_info in self.plotted_points:
            cont, ind = pt_info["scatter"].contains(event)
            if cont:
                lat = pt_info["lat"]
                long_val = pt_info["long"]
                coord_text = f"{lat}, {long_val}"

                # Copy to system clipboard via Tkinter
                self.clipboard_clear()
                self.clipboard_append(coord_text)
                self.update()

                self.status_label.configure(text=f"Copied to Clipboard:\n{coord_text}", text_color="#00FF00")
                self.after(3000, lambda: self.status_label.configure(text="Click a point to copy Lat/Long", text_color="white"))
                break

    def populate_map_filters(self, spot_df):
        self.clear_checkboxes()

        types = sorted(spot_df["type"].dropna().unique().tolist())
        for t in types:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.type_frame, text=t, variable=var, command=self.plot_map)
            cb.pack(anchor="w", pady=2)
            self.type_vars[t] = var

        rigs = sorted(spot_df["rigs"].dropna().unique().tolist())
        for r in rigs:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.rig_frame, text=f"{r} Rig(s)", variable=var, command=self.plot_map)
            cb.pack(anchor="w", pady=2)
            self.rig_vars[r] = var

    def update_map(self, choice):
        if choice == "--Select--":
            return
        df = self.controller.df
        self.active_spot_df = df[
            (df["system"] == self.sys_var.get()) &
            (df["planet"] == self.planet_var.get()) &
            (df["mining_spot_number"] == choice)
        ]
        self.populate_map_filters(self.active_spot_df)
        self.plot_map()


class InputPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.columnconfigure(1, weight=1)

        fields = [
            ("System", "system"),
            ("Planet", "planet"),
            ("Mining Spot #", "mining_spot_number"),
            ("Type", "type"),
            ("Rigs", "rigs"),
            ("Direction (From Deposit to Center)", "direction"),
            ("Distance (km)", "distance"),
            ("Latitude", "lat"),
            ("Longitude", "long")
        ]

        self.entries = {}

        for i, (label_text, field_key) in enumerate(fields):
            ctk.CTkLabel(self, text=label_text + ":", anchor="w").grid(row=i, column=0, padx=20, pady=8, sticky="w")

            if field_key in ["system", "planet", "mining_spot_number", "type", "rigs"]:
                combo = ctk.CTkComboBox(self, values=[])
                combo.grid(row=i, column=1, padx=20, pady=8, sticky="ew")
                self.entries[field_key] = combo
            else:
                entry = ctk.CTkEntry(self)
                entry.grid(row=i, column=1, padx=20, pady=8, sticky="ew")
                self.entries[field_key] = entry

        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)

        self.btn_save = ctk.CTkButton(self.btn_frame, text="Save", command=self.save_record, fg_color="green", hover_color="darkgreen")
        self.btn_save.pack(side="left", padx=10)

        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancel / Reset", command=self.reset_fields, fg_color="red", hover_color="darkred")
        self.btn_cancel.pack(side="left", padx=10)

    def refresh_dropdowns(self):
        df = self.controller.df
        for field in ["system", "planet", "mining_spot_number", "type", "rigs"]:
            if not df.empty and field in df.columns:
                existing_vals = sorted([str(x) for x in df[field].dropna().unique().tolist()])
            else:
                existing_vals = []
            self.entries[field].configure(values=existing_vals)

    def save_record(self):
        try:
            raw_dir = float(self.entries["direction"].get())
            calculated_dir = raw_dir + 180.0 if raw_dir < 180.0 else raw_dir - 180.0

            record = {
                "system": self.entries["system"].get().strip(),
                "planet": self.entries["planet"].get().strip(),
                "mining_spot_number": self.entries["mining_spot_number"].get().strip(),
                "type": self.entries["type"].get().strip(),
                "rigs": self.entries["rigs"].get().strip(),
                "direction": calculated_dir,
                "distance": float(self.entries["distance"].get()),
                "lat": float(self.entries["lat"].get()),
                "long": float(self.entries["long"].get())
            }

            new_df = pd.DataFrame([record])
            new_df.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)

            self.reset_fields()
            self.controller.df = load_data()
            print("Record Saved Successfully!")

        except ValueError:
            print("Error: Please enter valid numerical values for direction, distance, latitude, and longitude.")

    def reset_fields(self):
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkComboBox):
                widget.set("")
            else:
                widget.delete(0, "end")
        self.refresh_dropdowns()


class ManagePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Database Records Overview", font=("Arial", 18, "bold")).pack(anchor="w", padx=15, pady=10)

        self.table_scroll = ctk.CTkScrollableFrame(self)
        self.table_scroll.pack(fill="both", expand=True, padx=15, pady=5)

    def load_table_data(self):
        for widget in self.table_scroll.winfo_children():
            widget.destroy()

        df = load_data()
        self.controller.df = df

        if df.empty:
            ctk.CTkLabel(self.table_scroll, text="No records found in surfaceminingmap.csv").pack(pady=20)
            return

        headers = ["Row", "System", "Planet", "Spot #", "Type", "Rigs", "Dir (°)", "Dist (km)", "Lat", "Long", "Action"]

        for col_idx, header in enumerate(headers):
            lbl = ctk.CTkLabel(self.table_scroll, text=header, font=("Arial", 12, "bold"))
            lbl.grid(row=0, column=col_idx, padx=8, pady=5, sticky="ew")

        for row_idx, row in df.iterrows():
            values = [
                str(row_idx + 1),
                str(row["system"]),
                str(row["planet"]),
                str(row["mining_spot_number"]),
                str(row["type"]),
                str(row["rigs"]),
                f"{float(row['direction']):.1f}",
                f"{float(row['distance']):.2f}",
                f"{float(row['lat']):.4f}",
                f"{float(row['long']):.4f}"
            ]

            for col_idx, val in enumerate(values):
                cell = ctk.CTkLabel(self.table_scroll, text=val)
                cell.grid(row=row_idx + 1, column=col_idx, padx=8, pady=3, sticky="ew")

            del_btn = ctk.CTkButton(
                self.table_scroll,
                text="Delete",
                width=60,
                fg_color="red",
                hover_color="darkred",
                command=lambda r=row_idx: self.delete_record(r)
            )
            del_btn.grid(row=row_idx + 1, column=len(headers) - 1, padx=5, pady=3)

    def delete_record(self, row_index):
        df = load_data()
        if row_index in df.index:
            df = df.drop(index=row_index).reset_index(drop=True)
            df.to_csv(CSV_FILE, index=False)
            self.load_table_data()
            print(f"Record at row {row_index + 1} deleted successfully.")


if __name__ == "__main__":
    app = MiningMapApp()
    app.mainloop()
