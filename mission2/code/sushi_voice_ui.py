import threading
import tkinter as tk

from sushi_voice_master import main, RECORD_SECONDS, MIC_DEVICE

def start_recording():
    # ステータス表示を更新
    status_var.set(
        f"Recording... ({RECORD_SECONDS} seconds) [Device: {MIC_DEVICE}]"
    )
    start_button.config(state="disabled")

    def worker():
        try:
            # ここで sushi_voice_master.main() を実行
            # 中で録音 → 文字起こし → Gemini → ロボット実行までやる
            text, order = main()

            if order:
                result = f"認識結果: {order}"
            else:
                result = "注文を認識できませんでした。"
        except Exception as e:
            result = f"エラーが発生しました: {e}"

        # UI側の更新はメインスレッドに戻して実行
        def update_ui():
            status_var.set(result)
            start_button.config(state="normal")

        root.after(0, update_ui)

    # 別スレッドで処理開始（UIをブロックしない）
    threading.Thread(target=worker, daemon=True).start()


# ===== Tkinter で簡易UI構築 =====
root = tk.Tk()
root.title("Sushi Voice Master")

# ウィンドウサイズなどはお好みで
root.geometry("400x200")

title_label = tk.Label(root, text="Sushi Voice Master", font=("Helvetica", 16, "bold"))
title_label.pack(pady=10)

status_var = tk.StringVar(value="待機中")

start_button = tk.Button(
    root,
    text="🎤 ボイス受付開始",
    font=("Helvetica", 12),
    width=20,
    height=2,
    command=start_recording,
)
start_button.pack(pady=10)

status_label = tk.Label(root, textvariable=status_var, font=("Helvetica", 11))
status_label.pack(pady=10)

root.mainloop()
