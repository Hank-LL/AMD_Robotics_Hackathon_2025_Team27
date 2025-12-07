#!/usr/bin/env python3
"""
Voice recognition script that transcribes audio from microphone using faster-whisper
and recognizes sushi orders using Gemini API
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

# Sushi menu definition
SUSHI_MENU = ["egg", "tuna", "cucumber roll", "tempura (fried shrimp)"]

# HuggingFace configuration
HF_USERNAME = "your_hf_username"  # Replace with your HuggingFace username

# Sushi model paths (HuggingFace repositories)
SUSHI_MODEL_PATHS = {
    'egg': f'{HF_USERNAME}/ServeEggSushi',
    'tuna': f'{HF_USERNAME}/ServeTunaSushi',
    'tempura (fried shrimp)': f'{HF_USERNAME}/ServeTempuraSushi',
    'cucumber roll': f'{HF_USERNAME}/ServeCucumberRoll'
}

# Gemini API configuration (retrieved from environment variable)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY',"")

# Configuration
MODEL_SIZE = "small"     # "tiny", "base", "small", "medium", "large-v2", "large-v3"
DEVICE = "cpu"           # Use CPU for ROCm environment (faster-whisper only supports CUDA)
COMPUTE_TYPE = "int8"    # "int8" recommended for CPU
LANGUAGE = "en"          # "ja" (Japanese), "en" (English)
RECORD_SECONDS = 7       # Recording duration (seconds)

# Microphone settings
MIC_DEVICE = 5           # USB Microphone (USB PnP Audio Device)
MIC_SAMPLE_RATE = 48000  # Microphone sample rate
MIC_CHANNELS = 1         # Mono
WHISPER_SAMPLE_RATE = 16000  # Sample rate required by Whisper

def resample_audio(audio, orig_sr, target_sr):
    """Resample audio data"""
    if orig_sr == target_sr:
        return audio
    num_samples = int(len(audio) * target_sr / orig_sr)
    return signal.resample(audio, num_samples)

def execute_sushi_serving(orders):
    """
    Execute robot action to serve ordered sushi using LeRobot models
    """
    if not orders:
        print("No orders to execute.")
        return
    
    # Initialize ModelInference
    inference_runner = ModelInference(
        model_paths=SUSHI_MODEL_PATHS,
        robot_port='/dev/ttyACM2',
        robot_id='my_awsome_follower_arm',
        cameras="{top: {type: opencv, index_or_path: 8, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 10, width: 640, height: 480, fps: 30}}",
        cache_dir="./model_cache"
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
                task=f"Serve {order} sushi",
                repo_id=f"{HF_USERNAME}/eval_{order.replace(' ', '_')}",
                episode_time_s=20,
                num_episodes=1,
                display_data=True
            )
            print(f"✅ Successfully served: {order}")
        except Exception as e:
            print(f"❌ Failed to serve {order}: {e}")

def recognize_order_with_gemini(text):
    """
    Flexibly recognize order content using Gemini API
    """
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY environment variable is not set.")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')  # or 'gemini-2.0-flash'
    
    # Create prompt
    prompt = f"""
The following is a transcribed text of a customer's order voice at a sushi restaurant.
Please recognize the ordered sushi from this text and return it in JSON format.

Available menu:
{json.dumps(SUSHI_MENU, ensure_ascii=False)}

Customer's statement:
"{text}"

Instructions:
1. Identify ONLY ONE sushi item that the customer ordered from the menu
2. If multiple items are mentioned, select only the first or most prominent one
3. If there are expressions like "recommendation", "suggest", or "your choice", return "recommendation": true
4. If the text is unclear, infer the menu item with similar pronunciation
5. Must return in the following JSON format (no other explanation needed):

{{
    "order": "single sushi item name",
    "recommendation": true or false,
    "confidence": "high" or "medium" or "low"
}}
"""
    
    try:
        # Parse with Gemini API
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Extract JSON part (remove markdown code blocks)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        # Select randomly for recommendation case
        if result.get("recommendation", False):
            random_sushi = random.choice(SUSHI_MENU)
            print(f"\n💡 Today's recommendation is '{random_sushi}'!")
            result["order"] = random_sushi
        
        return result
    
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error: {e}")
        print(f"Response: {result_text}")
        return None
    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        return None

def main(status_callback=None):
    """
    Main entry point.

    status_callback が指定されている場合は、処理の段階ごとに
    status_callback(phase, **info) を呼び出します。
    """
    def notify(phase, **info):
        """UI側に状態を通知するための小さいヘルパー"""
        if status_callback is not None:
            try:
                status_callback(phase, **info)
            except Exception as e:
                print(f"[Status callback error @ {phase}]: {e}")

    # Load model
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
        device=MIC_DEVICE
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

    # Recognize order with Gemini API
    print("\n🤖 Analyzing order with Gemini API...")
    notify("recognizing")
    result = recognize_order_with_gemini(text)

    if result:
        order = result.get("order")
        confidence = result.get("confidence", "unknown")
        notify("recognized", text=text, order=order, confidence=confidence)

        print("\n" + "=" * 50)
        if order:
            print(f"【Order】 (Confidence: {confidence})")
            print(f"  ✓ {order}")
            print("=" * 50)

            # Execute robot serving
            print("\n🤖 Starting robot serving sequence...")
            notify("serving", order=order)
            execute_sushi_serving([order])
            notify("served", order=order)
        else:
            print("Order could not be recognized.")
            print(f"Menu: {', '.join(SUSHI_MENU)}")
            print("=" * 50)

        return text, order
    else:
        print("\n⚠️  Failed to recognize order")
        notify("failed", text=text)
        return text, None

if __name__ == "__main__":
    main()