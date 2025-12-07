#!/usr/bin/env python3
"""
Voice recognition script that transcribes audio from microphone using faster-whisper
and recognizes sushi orders using Gemini API.
Always returns one of the predefined menu items.
"""

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from scipy import signal
import google.generativeai as genai
import json
import os
import random
from model_inference import ModelInference

# Menu definition (sushi + drink)
SUSHI_MENU = ["egg", "tuna", "cucumber roll", "tempura (fried shrimp)", "greentea cup"]

# HuggingFace configuration
HF_USERNAME = "your_hf_username"  # Replace with your HuggingFace username

# Sushi model paths (HuggingFace repositories)
SUSHI_MODEL_PATHS = {
    "egg": f"{HF_USERNAME}/ServeEggSushi",
    "tuna": f"{HF_USERNAME}/ServeTunaSushi",
    "tempura (fried shrimp)": f"{HF_USERNAME}/ServeTempuraSushi",
    "cucumber roll": f"{HF_USERNAME}/ServeCucumberRoll",
    "greentea cup": f"{HF_USERNAME}/ServeTeacup",  # change to "HankLL/ServeTeacup" if fixed
}

# Gemini API configuration (retrieved from environment variable)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Whisper / audio configuration
MODEL_SIZE = "small"      # "tiny", "base", "small", "medium", "large-v2", "large-v3"
DEVICE = "cpu"            # Use CPU for ROCm environment (faster-whisper only supports CUDA)
COMPUTE_TYPE = "int8"     # "int8" recommended for CPU
LANGUAGE = "en"           # "ja" (Japanese), "en" (English)
RECORD_SECONDS = 7        # Recording duration (seconds)

# Microphone settings
MIC_DEVICE = 5            # USB Microphone (USB PnP Audio Device)
MIC_SAMPLE_RATE = 48000   # Microphone sample rate
MIC_CHANNELS = 1          # Mono
WHISPER_SAMPLE_RATE = 16000  # Sample rate required by Whisper


def resample_audio(audio, orig_sr, target_sr):
    """Resample audio data."""
    if orig_sr == target_sr:
        return audio
    num_samples = int(len(audio) * target_sr / orig_sr)
    return signal.resample(audio, num_samples)


def execute_sushi_serving(orders):
    """
    Execute robot action to serve ordered items using LeRobot models.
    `orders` is a list of menu names (e.g., ["egg"], ["greentea cup"]).
    """
    if not orders:
        # With current logic this should not happen, but keep the guard.
        print("No orders to execute.")
        return

    # Initialize ModelInference
    inference_runner = ModelInference(
        model_paths=SUSHI_MODEL_PATHS,
        robot_port="/dev/ttyACM2",
        robot_id="my_awsome_follower_arm",
        cameras="{top: {type: opencv, index_or_path: 8, width: 640, height: 480, fps: 30}, "
                "wrist: {type: opencv, index_or_path: 10, width: 640, height: 480, fps: 30}}",
        cache_dir="./model_cache",
    )

    # Cache models if not already cached
    print("\n📦 Checking model cache...")
    inference_runner.cache_models(model_names=orders)

    # Execute each order
    for order in orders:
        if order not in SUSHI_MODEL_PATHS:
            print(f"⚠️  No model available for: {order}")
            continue

        print(f"\n🍣 Preparing to serve: {order}")
        print(f"   Model: {SUSHI_MODEL_PATHS[order]}")

        try:
            inference_runner.run_inference(
                model_name=order,
                task=f"Serve {order}",
                repo_id=f"{HF_USERNAME}/eval_{order.replace(' ', '_')}",
                episode_time_s=20,
                num_episodes=1,
                display_data=True,
            )
            print(f"✅ Successfully served: {order}")
        except Exception as e:
            print(f"❌ Failed to serve {order}: {e}")


def recognize_order_with_gemini(text):
    """
    Recognize order content using Gemini API.

    This function always returns a dict with:
        {
            "order": "<one of SUSHI_MENU>",
            "confidence": "high" | "medium" | "low"
        }
    If Gemini or JSON parsing fails, it falls back to a random menu item.
    """
    # Fallback in case of any error
    def fallback_result(reason: str):
        order = random.choice(SUSHI_MENU)
        print(f"⚠️  Falling back to random menu item due to: {reason}")
        print(f"   Selected fallback order: {order}")
        return {"order": order, "confidence": "low"}

    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY environment variable is not set.")
        return fallback_result("missing GEMINI_API_KEY")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")  # or 'gemini-2.0-flash'

        # Create prompt
        prompt = f"""
The following is a transcribed text of a customer's spoken order at a sushi restaurant.
Please recognize the ordered item from this text and return it in JSON format.

Available menu:
{json.dumps(SUSHI_MENU, ensure_ascii=False)}

Customer's statement:
"{text}"

Instructions:
1. Identify ONLY ONE item that the customer ordered from the menu.
2. If multiple items are mentioned, select only the first or most prominent one.
3. If the text is unclear, infer the menu item with similar pronunciation.
4. You MUST return only the following JSON object (no extra explanation):

{{
    "order": "single item name",
    "confidence": "high" or "medium" or "low"
}}
"""

        # Call Gemini and parse
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Extract JSON part (remove markdown code blocks)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)

        # Normalize and enforce that order is one of SUSHI_MENU
        order = result.get("order")
        confidence = result.get("confidence", "unknown")

        if not order or order not in SUSHI_MENU:
            # If Gemini returns something unexpected, fall back to random menu item
            return fallback_result("order not in SUSHI_MENU")

        return {"order": order, "confidence": confidence}

    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error: {e}")
        return fallback_result("JSON parsing error")
    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        return fallback_result("Gemini API error")


def main(status_callback=None):
    """
    Main entry point.

    If `status_callback` is provided, it will be called at each processing phase as:
        status_callback(phase, **info)
    so that a UI can reflect the current state.
    """

    def notify(phase, **info):
        """Small helper to send status updates to the UI via status_callback."""
        if status_callback is not None:
            try:
                status_callback(phase, **info)
            except Exception as e:
                print(f"[Status callback error @ {phase}]: {e}")

    # Load Whisper model
    notify("loading_model")
    print(f"Loading Whisper model: {MODEL_SIZE}...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("Loading complete\n")
    notify("model_loaded")

    # Record audio
    print(f"Recording... ({RECORD_SECONDS} seconds) [Device: {MIC_DEVICE}]")
    notify("recording_started", seconds=RECORD_SECONDS, device=MIC_DEVICE)

    audio = sd.rec(
        int(RECORD_SECONDS * MIC_SAMPLE_RATE),
        samplerate=MIC_SAMPLE_RATE,
        channels=MIC_CHANNELS,
        dtype=np.float32,
        device=MIC_DEVICE,
    )
    sd.wait()
    print("Recording complete\n")
    notify("recording_finished")

    # Resample (48kHz → 16kHz)
    audio_16k = resample_audio(audio.flatten(), MIC_SAMPLE_RATE, WHISPER_SAMPLE_RATE)

    # Transcribe
    print("Transcribing...")
    notify("transcribing")
    segments, _ = model.transcribe(audio_16k, language=LANGUAGE, vad_filter=True)

    text = "".join([seg.text for seg in segments]).strip()
    notify("transcribed", text=text)

    print("\n" + "=" * 50)
    print(f"Recognition result: {text}")
    print("=" * 50)

    # Recognize order with Gemini API (or fallback)
    print("\n🤖 Analyzing order with Gemini API...")
    notify("recognizing")
    result = recognize_order_with_gemini(text)

    # With the current implementation, result is always a dict with a valid menu item.
    order = result["order"]
    confidence = result.get("confidence", "unknown")
    notify("recognized", text=text, order=order, confidence=confidence)

    print("\n" + "=" * 50)
    print(f"[Order] (Confidence: {confidence})")
    print(f"  ✓ {order}")
    print("=" * 50)

    # Execute robot serving
    print("\n🤖 Starting robot serving sequence...")
    notify("serving", order=order)
    execute_sushi_serving([order])
    notify("served", order=order)

    return text, order


if __name__ == "__main__":
    main()
