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


# ===== Variables for labels, buttons, and sushi image =====
status_var = tk.StringVar(value="Idle")
result_var = tk.StringVar(value="No order yet.")

# We need to keep references to the PhotoImage objects,
# otherwise they will be garbage-collected.
item_photo = None
item_image_id = None

# Soft background color that blends with the main image (tweak as you like)
TEXT_BG = "#f8f4e8"


def get_image_path_for_order(order: str) -> str:
    """
    Map an order string (e.g., 'Egg', 'Tuna') to an image file.
    Default: lower-case, spaces -> underscores, then {name}.png
    """
    # Custom mapping if you want special names
    order_map = {
        "egg": "egg.png",
        "tempura (fried shrimp)": "tempura_fried_shrimp.png",
        "tuna": "tuna.png",
        "cucumber roll": "cucumber_roll.png"
    }

    key = order.lower().strip()
    key_simple = key.replace(" ", "_")

    filename = order_map.get(key, f"{key_simple}.png")
    return os.path.join(IMAGES_DIR, filename)


def show_sushi_image(order: str):
    """
    Load and display the sushi image that matches the given order
    (e.g., Egg -> egg.png, Tuna -> tuna.png).
    """
    global item_photo, item_image_id

    if not order:
        return

    img_path = get_image_path_for_order(order)

    try:
        img = Image.open(img_path)
    except FileNotFoundError:
        # If there is no image for this order, just skip.
        status_var.set(f"Image not found for order: {order}")
        return

    # Resize image to fit nicely in the center area
    max_width = int(bg_width * 0.35)
    max_height = int(bg_height * 0.35)
    img.thumbnail((max_width, max_height), Image.LANCZOS)

    item_photo = ImageTk.PhotoImage(img)

    if item_image_id is None:
        # Place the sushi image roughly in the center of the beige area
        cx = bg_width // 2
        cy = int(bg_height * 0.60)
        item_image_id = canvas.create_image(cx, cy, image=item_photo, anchor="center")
    else:
        canvas.itemconfigure(item_image_id, image=item_photo)


# ===== Labels =====
instruction_label = tk.Label(
    root,
    text="Press the button to place your order.",
    font=("Arial", 20, "bold"),   # bigger & bold
    bg=TEXT_BG,
    fg="#000000",
)
status_label = tk.Label(
    root,
    textvariable=status_var,
    font=("Arial", 16, "bold"),   # bigger & bold
    bg=TEXT_BG,
    fg="#000000",
)
result_label = tk.Label(
    root,
    textvariable=result_var,
    font=("Arial", 16, "italic"),  # bigger & italic
    bg=TEXT_BG,
    fg="#000000",
)


def start_recording():
    """Callback when the button is pressed → start voice order."""

    status_var.set("Listening... Please speak your order.")
    result_var.set("Waiting for your voice...")
    start_button.config(state="disabled")

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
                    # Show matching sushi image
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

        # Safely update the UI from the main thread
        root.after(0, update)

    def worker():
        """Run the heavy processing (recording + decoding) in a separate thread."""
        try:
            text, order = main(status_callback=status_callback)

            def finalize():
                if order:
                    status_var.set("Order completed.")
                    result_var.set(f"Final order: {order}")
                    # Ensure final order image is shown
                    show_sushi_image(order)
                else:
                    status_var.set("Sorry, we could not understand your order.")
                    result_var.set("Please try again.")
                start_button.config(state="normal")

            root.after(0, finalize)

        except Exception as e:
            def on_error():
                status_var.set("Error occurred.")
                result_var.set(f"Error: {e}")
                start_button.config(state="normal")

            root.after(0, on_error)

    threading.Thread(target=worker, daemon=True).start()


start_button = tk.Button(
    root,
    text="🎤 Start Voice Order",
    font=("Arial", 18, "bold"),   # bigger & bold
    width=20,
    height=2,
    relief="raised",
    command=start_recording,
)

# ===== Place widgets on the canvas =====
center_x = bg_width // 2

# Slightly higher instruction, then button, then sushi image (centered by show_sushi_image),
# and finally the status/result near the bottom.
canvas.create_window(center_x, int(bg_height * 0.33), window=instruction_label)
canvas.create_window(center_x, int(bg_height * 0.50), window=start_button)
canvas.create_window(center_x, int(bg_height * 0.82), window=status_label)
canvas.create_window(center_x, int(bg_height * 0.90), window=result_label)

root.mainloop()
