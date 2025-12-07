import os
import threading
import tkinter as tk
from PIL import Image, ImageTk

from sushi_voice_master import main, RECORD_SECONDS, MIC_DEVICE


# ===== パス設定（sushi_voice_ui.py の1つ上の階層にある images/ を見る） =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_IMAGE = os.path.join(SCRIPT_DIR, "..", "images", "amd_sushi_bg.png")
# もし sushi_voice_ui.py がプロジェクト直下にある場合は、上の行を
# BACKGROUND_IMAGE = os.path.join(SCRIPT_DIR, "images", "amd_sushi_bg.png")
# に変えてください。


# ===== Tk ウィンドウ作成 =====
root = tk.Tk()
root.title("AMD Sushi Voice Order")

# 背景画像読み込み
try:
    bg_image = Image.open(BACKGROUND_IMAGE)
except FileNotFoundError as e:
    raise SystemExit(f"Background image not found: {BACKGROUND_IMAGE}") from e

bg_width, bg_height = bg_image.size

# ウィンドウサイズを画像に合わせる
root.geometry(f"{bg_width}x{bg_height}")

# Canvas に背景画像を貼る
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


# ===== ラベル・ボタン用の変数 =====
status_var = tk.StringVar(value="Idle")
result_var = tk.StringVar(value="No order yet.")

# 背景となじむ淡い色（好みで調整OK）
TEXT_BG = "#f8f4e8"

instruction_label = tk.Label(
    root,
    text="Press the button to place your order.",
    font=("Helvetica", 13, "bold"),
    bg=TEXT_BG,
)
status_label = tk.Label(
    root,
    textvariable=status_var,
    font=("Helvetica", 11),
    bg=TEXT_BG,
)
result_label = tk.Label(
    root,
    textvariable=result_var,
    font=("Helvetica", 11, "italic"),
    bg=TEXT_BG,
)


def start_recording():
    """Button pressed → start voice order"""

    status_var.set("Listening... Please speak your order.")
    result_var.set("Waiting for your voice...")
    start_button.config(state="disabled")

    def status_callback(phase, **info):
        """sushi_voice_master から状態通知を受けて UI を更新"""
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

        # UIスレッドで安全に更新
        root.after(0, update)

    def worker():
        """重い処理を別スレッドで実行"""
        try:
            text, order = main(status_callback=status_callback)

            def finalize():
                if order:
                    status_var.set("Order completed.")
                    result_var.set(f"Final order: {order}")
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
    font=("Helvetica", 12, "bold"),
    width=20,
    height=2,
    relief="raised",
    command=start_recording,
)

# ===== Canvas上にウィジェットを配置 =====
center_x = bg_width // 2

canvas.create_window(center_x, int(bg_height * 0.40), window=instruction_label)
canvas.create_window(center_x, int(bg_height * 0.55), window=start_button)
canvas.create_window(center_x, int(bg_height * 0.70), window=status_label)
canvas.create_window(center_x, int(bg_height * 0.80), window=result_label)

root.mainloop()
