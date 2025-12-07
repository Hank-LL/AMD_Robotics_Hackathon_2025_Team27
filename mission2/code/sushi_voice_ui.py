import os
import threading
import tkinter as tk
from PIL import Image, ImageTk

from sushi_voice_master import main, RECORD_SECONDS, MIC_DEVICE


# ===== Path settings (look for images/ one level above sushi_voice_ui.py) =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, "..", "images")
BACKGROUND_IMAGE = os.path.join(IMAGES_DIR, "amd_sushi_bg.png")


# ===== Create Tk window =====
root = tk.Tk()
root.title("Sushi Voice Order")

# Load background image
try:
    bg_image = Image.open(BACKGROUND_IMAGE)
except FileNotFoundError as e:
    raise SystemExit(f"Background image not found: {BACKGROUND_IMAGE}") from e

bg_width, bg_height = bg_image.size

# Set window size to match the image size
root.geometry(f"{bg_width}x{bg_height}")

# Create canvas and draw background image
canvas = tk.Canvas(
    root,
    width=bg_width,
    height=bg_height,
    highlightthickness=0,
    bd=0,
)
canvas.pack(fill="both", expand=True)

bg_photo = ImageTk.PhotoImage(bg_image)
canvas.create_image(0, 0, image=bg_photo, anchor="nw")


# ===== Layout positions (left / center / right columns) =====
LEFT_X = int(bg_width * 0.18)
CENTER_X = int(bg_width * 0.50)
RIGHT_X = int(bg_width * 0.82)
CENTER_Y = int(bg_height * 0.55)  # general vertical center of beige area


# ===== Variables for labels, status, and sushi image =====
status_var = tk.StringVar(value="Idle")
result_var = tk.StringVar(value="No order yet.")

item_photo = None          # keep reference to sushi ImageTk
item_image_id = None       # canvas id for sushi image

# Soft background color that blends with the main image (tweak as you like)
TEXT_BG = "#f8f4e8"


def get_image_path_for_order(order: str) -> str:
    """
    Map an order string (e.g., 'Egg', 'Tuna') to an image file.
    Default: lower-case, spaces -> underscores, then {name}.png
    """
    order_map = {
        "egg": "egg.png",
        "tuna": "tuna.png",
        "cucumber roll": "cucumber_roll.png",
        "tempura (fried shrimp)": "tempura.png",
        "tempura": "tempura.png",  # extra alias, just in case
    }

    key = order.lower().strip()
    key_simple = key.replace(" ", "_")

    filename = order_map.get(key, f"{key_simple}.png")
    return os.path.join(IMAGES_DIR, filename)


def show_sushi_image(order: str):
    """
    Load and display the sushi image that matches the given order
    (e.g., Egg -> egg.png, Tuna -> tuna.png) on the right side.
    """
    global item_photo, item_image_id

    if not order:
        return

    img_path = get_image_path_for_order(order)

    try:
        img = Image.open(img_path)
    except FileNotFoundError:
        status_var.set(f"Image not found for order: {order}")
        return

    # Resize image to fit nicely in the center-right area
    max_width = int(bg_width * 0.30)
    max_height = int(bg_height * 0.35)
    img.thumbnail((max_width, max_height), Image.LANCZOS)

    item_photo = ImageTk.PhotoImage(img)

    if item_image_id is None:
        cx = RIGHT_X
        cy = CENTER_Y
        item_image_id = canvas.create_image(cx, cy, image=item_photo, anchor="center")
    else:
        canvas.itemconfigure(item_image_id, image=item_photo)


# ===== Labels (placed in the center column) =====
instruction_label = tk.Label(
    root,
    text="Press the button on the left to place your order.",
    font=("Arial", 28, "bold"),
    bg=TEXT_BG,
    fg="#000000",
    wraplength=int(bg_width * 0.5),
)
status_label = tk.Label(
    root,
    textvariable=status_var,
    font=("Arial", 20, "bold"),
    bg=TEXT_BG,
    fg="#000000",
    wraplength=int(bg_width * 0.5),
)
result_label = tk.Label(
    root,
    textvariable=result_var,
    font=("Arial", 20, "italic"),
    bg=TEXT_BG,
    fg="#000000",
    wraplength=int(bg_width * 0.5),
)


# ===== Round "button" drawn on the canvas (left side) =====
button_circle_id = None
button_text_id = None
button_enabled = True


def set_button_enabled(enabled: bool):
    """Enable/disable the round button (change color & state flag)."""
    global button_enabled
    button_enabled = enabled

    fill = "#ffffff" if enabled else "#cccccc"
    cursor = "hand2" if enabled else "arrow"

    if button_circle_id is not None:
        canvas.itemconfigure(button_circle_id, fill=fill)
        canvas.itemconfigure(button_text_id, fill="#000000")
        canvas.itemconfigure(button_circle_id, state="normal")
        canvas.itemconfigure(button_text_id, state="normal")
        canvas.itemconfigure(button_circle_id, tags=("round_button",))
        canvas.itemconfigure(button_text_id, tags=("round_button_text",))

    canvas.config(cursor=cursor)


def on_round_button_hover(enter: bool):
    """Change color slightly on hover when enabled."""
    if not button_enabled or button_circle_id is None:
        return
    fill = "#ffe4b5" if enter else "#ffffff"
    canvas.itemconfigure(button_circle_id, fill=fill)


def on_round_button_click(event):
    """Handle click on the round button."""
    if not button_enabled:
        return
    start_recording()


def create_round_button():
    """Draw a round button on the left side of the canvas."""
    global button_circle_id, button_text_id

    radius = int(min(bg_width, bg_height) * 0.10)  # relative size
    cx = LEFT_X
    cy = CENTER_Y

    x0 = cx - radius
    y0 = cy - radius
    x1 = cx + radius
    y1 = cy + radius

    button_circle_id = canvas.create_oval(
        x0,
        y0,
        x1,
        y1,
        fill="#ffffff",
        outline="#000000",
        width=3,
    )

    button_text_id = canvas.create_text(
        cx,
        cy,
        text="Start\nVoice Order",
        font=("Arial", 18, "bold"),
        fill="#000000",
        justify="center",
    )

    # Bind events for both the circle and the text
    for item in (button_circle_id, button_text_id):
        canvas.tag_bind(item, "<Button-1>", on_round_button_click)
        canvas.tag_bind(
            item,
            "<Enter>",
            lambda e: on_round_button_hover(True),
        )
        canvas.tag_bind(
            item,
            "<Leave>",
            lambda e: on_round_button_hover(False),
        )

    set_button_enabled(True)


def start_recording():
    """Callback called when the round button is pressed → start voice order."""
    status_var.set("Listening... Please speak your order.")
    result_var.set("Waiting for your voice...")
    set_button_enabled(False)

    def status_callback(phase, **info):
        """Receive status updates from sushi_voice_master and update the UI."""
        def update():
            if phase == "recording_started":
                status_var.set(
                    f"Listening... Please speak your order. "
                    f"({RECORD_SECONDS} seconds)"
                )
            elif phase == "recording_finished":
                status_var.set("Recording finished. Decoding your order, please wait...")
            elif phase == "transcribing":
                status_var.set("Decoding your voice, please wait...")
            elif phase == "recognizing":
                status_var.set("Understanding your order, please wait...")
            elif phase == "recognized":
                order = info.get("order")
                if order:
                    status_var.set("Order recognized.")
                    result_var.set(f"Order recognized: {order}")
                    show_sushi_image(order)
                else:
                    status_var.set("Could not recognize your order.")
                    result_var.set("Could not recognize your order.")
            elif phase == "failed":
                status_var.set("Could not understand the audio.")
                result_var.set("No valid order was recognized.")
            elif phase == "serving":
                order = info.get("order")
                status_var.set(f"Serving the robot: {order} ...")
            elif phase == "served":
                order = info.get("order")
                status_var.set(f"Robot finished serving: {order}")

        root.after(0, update)

    def worker():
        """Run the heavy processing (recording + decoding) in a separate thread."""
        try:
            text, order = main(status_callback=status_callback)

            def finalize():
                if order:
                    status_var.set("Order completed.")
                    result_var.set(f"Final order: {order}")
                    show_sushi_image(order)
                else:
                    status_var.set("Sorry, we could not understand your order.")
                    result_var.set("Please try again.")
                set_button_enabled(True)

            root.after(0, finalize)

        except Exception as e:
            def on_error():
                status_var.set("Error occurred.")
                result_var.set(f"Error: {e}")
                set_button_enabled(True)

            root.after(0, on_error)

    threading.Thread(target=worker, daemon=True).start()


# ===== Place labels on the canvas (center column) =====
canvas.create_window(CENTER_X, int(bg_height * 0.32), window=instruction_label)
canvas.create_window(CENTER_X, int(bg_height * 0.50), window=status_label)
canvas.create_window(CENTER_X, int(bg_height * 0.68), window=result_label)

# ===== Create the round button on the left =====
create_round_button()

root.mainloop()
