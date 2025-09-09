import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from datetime import datetime
import math

# ------------------ CONFIG ------------------
BAUDRATE = 9600
running = False
ser = None
data_values = []
relay_status = "OFF"
log_file = "soil_moisture_log.csv"

# Create CSV log file with header
with open(log_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Moisture %", "Relay Status"])

# ------------------ SERIAL ------------------
def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def connect_serial():
    global ser, running
    port = port_combo.get()
    if not port:
        messagebox.showerror("Error", "Select a COM port first!")
        return
    try:
        ser = serial.Serial(port, BAUDRATE, timeout=1)
        running = True
        threading.Thread(target=read_serial, daemon=True).start()
        connect_btn.config(state="disabled")
        disconnect_btn.config(state="normal")
        ack_var.set(f"Connected to {port}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open {port}\n{e}")

def disconnect_serial():
    global running, ser
    running = False
    if ser:
        ser.close()
        ser = None
    connect_btn.config(state="normal")
    disconnect_btn.config(state="disabled")
    ack_var.set("Disconnected")

def read_serial():
    global ser, running, data_values, relay_status
    buffer = ""
    while running and ser:
        try:
            buffer += ser.read(ser.in_waiting or 1).decode("utf-8", errors='ignore')
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line.startswith("LEVEL:"):
                    parts = line.replace(" ","").split(",")
                    moisture = int(parts[0].split(":")[1])
                    relay_status = parts[1].split(":")[1]
                    update_gui(moisture, relay_status)
                elif line.startswith("ACK_MIN") or line.startswith("ACK_MAX"):
                    ack_var.set(line)
        except Exception:
            pass
        time.sleep(0.05)

# ------------------ GUI UPDATE ------------------
def update_gui(moisture, relay):
    global data_values
    moisture_var.set(f"{moisture}%")
    # Update relay indicator
    if relay == "ON":
        relay_label.config(background="green")
    else:
        relay_label.config(background="red")

    # Update gauge
    draw_gauge(moisture)

    # Update graph
    data_values.append(moisture)
    if len(data_values) > 100:
        data_values = data_values[-100:]
    ax.clear()
    ax.plot(data_values, marker='o', linestyle='-', color='green')
    ax.set_ylim(0,100)
    ax.set_ylabel("Moisture %")
    ax.set_title("Soil Moisture Trend", fontweight='bold')
    canvas.draw()

    # Log CSV
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), moisture, relay])

# ------------------ GAUGE DRAW ------------------
def draw_gauge(value):
    gauge_canvas.delete("all")
    x0, y0 = 150, 150
    r = 120
    start_angle = 135
    end_angle = 45
    # Draw background arc
    gauge_canvas.create_arc(x0-r, y0-r, x0+r, y0+r, start=start_angle, extent=270, style="arc", width=20, outline="#ddd")
    # Draw filled arc based on value
    extent_val = (value/100)*270
    gauge_canvas.create_arc(x0-r, y0-r, x0+r, y0+r, start=start_angle, extent=extent_val, style="arc", width=20, outline="#4CAF50")
    # Draw text
    gauge_canvas.create_text(x0, y0, text=f"{value}%", font=("Arial",24,"bold"))

# ------------------ COMMANDS ------------------
def send_command(cmd):
    if ser and ser.is_open:
        ser.write((cmd+"\n").encode('utf-8'))

def set_thresholds():
    try:
        min_val = min_slider.get()
        max_val = max_slider.get()
        if 0 <= min_val < max_val <= 100:
            send_command(f"SET_MIN:{min_val}")
            send_command(f"SET_MAX:{max_val}")
            ack_var.set(f"Thresholds sent: Min={min_val}, Max={max_val}")
        else:
            messagebox.showerror("Error","Min < Max and both 0-100")
    except:
        messagebox.showerror("Error","Invalid threshold values")

# ------------------ GUI ------------------
root = tk.Tk()
root.title("🌱 Smart Garden Dashboard")
root.geometry("1300x750")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TLabel", font=("Arial",12))
style.configure("TButton", font=("Arial",12), padding=5)
style.configure("TScale", background="#f0f0f0")

# Top Bar
top_frame = ttk.Frame(root, padding=10)
top_frame.pack(side="top", fill="x")
ttk.Label(top_frame, text="🌱 Smart Garden Dashboard", font=("Arial",20,"bold")).pack(side="left")
ack_var = tk.StringVar()
ttk.Label(top_frame, textvariable=ack_var, font=("Arial",12), foreground="blue").pack(side="right")

# Main Frame
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# Left Controls Panel
control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
control_frame.grid(row=0, column=0, sticky="ns")
control_frame.columnconfigure(0, weight=1)

moisture_var = tk.StringVar(value="0%")
relay_label = tk.Label(control_frame, text="RELAY", width=12, font=("Arial",14,"bold"), background="red", foreground="white")
relay_label.grid(row=0,column=0,pady=5)

ttk.Button(control_frame,text="Auto Mode",command=lambda: send_command("AUTO")).grid(row=1,column=0,pady=5, sticky="ew")
ttk.Button(control_frame,text="Force ON",command=lambda: send_command("FORCE_ON")).grid(row=2,column=0,pady=5, sticky="ew")
ttk.Button(control_frame,text="Force OFF",command=lambda: send_command("FORCE_OFF")).grid(row=3,column=0,pady=5, sticky="ew")

# Threshold sliders
ttk.Label(control_frame,text="Auto Min %").grid(row=4,column=0,pady=2)
min_slider = tk.Scale(control_frame, from_=0, to=100, orient="horizontal", length=180)
min_slider.set(40)
min_slider.grid(row=5,column=0,pady=5)
ttk.Label(control_frame,text="Auto Max %").grid(row=6,column=0,pady=2)
max_slider = tk.Scale(control_frame, from_=0, to=100, orient="horizontal", length=180)
max_slider.set(85)
max_slider.grid(row=7,column=0,pady=5)
ttk.Button(control_frame,text="Set Thresholds", command=set_thresholds).grid(row=8,column=0,pady=5, sticky="ew")

# Serial COM Port
ttk.Label(control_frame,text="Serial Port").grid(row=9,column=0,pady=2)
port_combo = ttk.Combobox(control_frame, values=list_serial_ports())
port_combo.grid(row=10,column=0,pady=5)
connect_btn = ttk.Button(control_frame,text="Connect", command=connect_serial)
connect_btn.grid(row=11,column=0,pady=5, sticky="ew")
disconnect_btn = ttk.Button(control_frame,text="Disconnect", command=disconnect_serial, state="disabled")
disconnect_btn.grid(row=12,column=0,pady=5, sticky="ew")

# Center Panel - Gauge
center_frame = ttk.LabelFrame(main_frame, text="Moisture Gauge", padding=10)
center_frame.grid(row=0, column=1, sticky="nsew")
center_frame.columnconfigure(0, weight=1)
center_frame.rowconfigure(0, weight=1)

gauge_canvas = tk.Canvas(center_frame, width=300, height=300)
gauge_canvas.pack(expand=True, fill="both", padx=10, pady=10)

# Right Panel - Graph
right_frame = ttk.LabelFrame(main_frame, text="Moisture Trend", padding=10)
right_frame.grid(row=0, column=2, sticky="nsew")
right_frame.columnconfigure(0, weight=1)
right_frame.rowconfigure(0, weight=1)

fig, ax = plt.subplots(figsize=(6,4))
canvas = FigureCanvasTkAgg(fig, master=right_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

# ------------------ Close ------------------
def on_close():
    disconnect_serial()
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
