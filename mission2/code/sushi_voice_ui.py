import threading
import tkinter as tk

from sushi_voice_master import main, RECORD_SECONDS, MIC_DEVICE

# ===== Tkinter UI =====

root = tk.Tk()
root.title("Sushi Voice Order")
root.geometry("420x260")

title_label = tk.Label(root, text="Sushi Voice Order", font=("Helvetica", 16, "bold"))
title_label.pack(pady=10)

instruction_label = tk.Label(
    root,
    text="Press the button to place your order.",
    font=("Helvetica", 11),
)
instruction_label.pack(pady=5)

status_var = tk.StringVar(value="Idle")
status_label = tk.Label(root, textvariable=status_var, font=("Helvetica", 11))
status_label.pack(pady=5)

result_var = tk.StringVar(value="No order yet.")
result_label = tk.Label(root, textvariable=result_var, font=("Helvetica", 11, "italic"))
result_label.pack(pady=5)


def start_recording():
    """Button pressed → start voice order"""

    # 状態リセット＆ボタン無効化
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
            # loading_model / model_loaded は必要なら追加してもOK

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
    font=("Helvetica", 12),
    width=22,
    height=2,
    command=start_recording,
)
start_button.pack(pady=15)

root.mainloop()
