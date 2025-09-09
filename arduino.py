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

BAUDRATE = 9600
running = False
ser = None
data_values = []
relay_status = "OFF"

# Logging CSV
log_file = "soil_moisture_log.csv"
with open(log_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Moisture %", "Relay Status"])

# Serial Handling
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

def read_serial():
    global ser, running, data_values, relay_status
    while running and ser:
        try:
            line = ser.readline().decode("utf-8").strip()
            if line.startswith("LEVEL:"):
                parts = line.replace(" ", "").split(",")
                moisture = int(parts[0].split(":")[1])
                relay_status = parts[1].split(":")[1]
                update_gui(moisture, relay_status)
        except Exception:
            pass
        time.sleep(0.1)

def update_gui(moisture, relay):
    global data_values
    moisture_var.set(f"{moisture}%")
    progress["value"] = moisture
    relay_var.set(f"Relay: {relay}")
    data_values.append(moisture)
    if len(data_values) > 50:
        data_values = data_values[-50:]
    ax.clear()
    ax.plot(data_values, marker='o', linestyle='-', color='green')
    ax.set_ylim(0,100)
    ax.set_ylabel("Moisture %")
    ax.set_title("Soil Moisture Trend")
    canvas.draw()
    # Log to CSV
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), moisture, relay])

# Commands
def send_command(cmd):
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode('utf-8'))

def set_thresholds():
    try:
        min_val = int(min_entry.get())
        max_val = int(max_entry.get())
        if 0 <= min_val < max_val <= 100:
            send_command(f"SET_MIN:{min_val}")
            send_command(f"SET_MAX:{max_val}")
            messagebox.showinfo("Success", f"Thresholds set: Min={min_val}, Max={max_val}")
        else:
            messagebox.showerror("Error","Min < Max and both 0-100")
    except:
        messagebox.showerror("Error","Invalid threshold values")


# GUI
root = tk.Tk()
root.title("🌱 Smart Garden Dashboard")

mainframe = ttk.Frame(root, padding="10")
mainframe.grid(row=0,column=0,sticky="nsew")

moisture_var = tk.StringVar(value="0%")
relay_var = tk.StringVar(value="Relay: OFF")
ttk.Label(mainframe, text="Soil Moisture:").grid(row=0,column=0,sticky="w")
ttk.Label(mainframe, textvariable=moisture_var, font=("Arial",16)).grid(row=0,column=1)
ttk.Label(mainframe, textvariable=relay_var, font=("Arial",12)).grid(row=1,column=0,columnspan=2,sticky="w")

progress = ttk.Progressbar(mainframe, orient="vertical", length=200, mode="determinate", maximum=100)
progress.grid(row=2,column=0,rowspan=3,padx=10)

# Buttons
ttk.Button(mainframe,text="Auto Mode",command=lambda: send_command("AUTO")).grid(row=2,column=1,pady=5)
ttk.Button(mainframe,text="Force ON",command=lambda: send_command("FORCE_ON")).grid(row=3,column=1,pady=5)
ttk.Button(mainframe,text="Force OFF",command=lambda: send_command("FORCE_OFF")).grid(row=4,column=1,pady=5)

# Thresholds
ttk.Label(mainframe,text="Auto Min %:").grid(row=5,column=0)
min_entry = ttk.Entry(mainframe,width=5)
min_entry.grid(row=5,column=1)
min_entry.insert(0,"40")

ttk.Label(mainframe,text="Auto Max %:").grid(row=6,column=0)
max_entry = ttk.Entry(mainframe,width=5)
max_entry.grid(row=6,column=1)
max_entry.insert(0,"85")

ttk.Button(mainframe,text="Set Thresholds",command=set_thresholds).grid(row=7,column=0,columnspan=2,pady=5)

# Serial port
ttk.Label(mainframe,text="Serial Port:").grid(row=8,column=0)
port_combo = ttk.Combobox(mainframe, values=list_serial_ports())
port_combo.grid(row=8,column=1)
connect_btn = ttk.Button(mainframe,text="Connect",command=connect_serial)
connect_btn.grid(row=9,column=0,pady=5)
disconnect_btn = ttk.Button(mainframe,text="Disconnect",command=disconnect_serial,state="disabled")
disconnect_btn.grid(row=9,column=1,pady=5)

# Graph
fig,ax = plt.subplots(figsize=(5,3))
canvas = FigureCanvasTkAgg(fig, master=mainframe)
canvas.get_tk_widget().grid(row=0,column=2,rowspan=10,padx=10)

def on_close():
    disconnect_serial()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
