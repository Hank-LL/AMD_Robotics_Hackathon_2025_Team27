# AMD_Robotics_Nakano Club  
**Title:** AMD Robotics Hackathon 2025 – Sushi Master

**Team:** 中野同好会 (Nakano Club)  
- Yuya Matsuda (松田 侑也)  
- Daichi Kiyozaki (清崎 大地)  
- Ryota Watanabe (渡邉 稜大)  
- Mitsuki Takaoka (高岡 充伎)  

---

## Task Summary

- **Overview**
  - Voice-driven sushi serving system using SO-101 robot arm and multi-model routing via Hugging Face.

- **Task Definition**
  - The robot handles five types of sushi-related tasks:
    - Tuna sushi
    - Egg sushi
    - Tempura sushi
    - Cucumber roll
    - Green tea

- **Serving Flow**
  1. Receive a sushi order via microphone in natural language  
     (e.g., “tuna please”, “the red one”, “vegan option”, “something for kids”).
  2. Interpret the order, select the appropriate model, and execute the serving motion:

| Item                      | Task Description                                   |
|---------------------------|----------------------------------------------------|
| 🥚 Egg Sushi              | Place topping on sushi rice, then serve on plate  |
| 🐟 Tuna Sushi             | Place topping on sushi rice, then serve on plate  |
| 🥒 Cucumber Roll          | Serve roll directly on plate                      |
| 🍤 Tempura (Fried Shrimp) | Place topping on sushi rice, then serve on plate  |
| 🧉 Greentea Cup           | Serve cup directly next to plate                  |

---

## Submission Details

### 1. Mission Description  
*Real world application of your mission*

Our mission is to build a **multi-model, voice-driven sushi serving assistant** that fuses speech recognition, language understanding, and per-dish robot policies into a single seamless system for real food service environments.

- Target scenarios:
  - Sushi counters where repetitive “pick-and-place” style tasks are common.
  - Environments that must handle high customer throughput with limited staff.
- Social impact:
  - The system aims to help address labor shortages in the Japanese food service industry by automating simple serving tasks.
  - By using **speech as the main interface**, it lowers the barrier for:
    - Elderly customers
    - Children
    - Foreign tourists who struggle with Japanese or complex touch-panel UIs.
- Robotics perspective:
  - The project showcases a pipeline from **speech recognition → language understanding → task selection → robot execution** on a real arm, using commodity hardware (RGB cameras, microphone, consumer PC).

---

### 2. Creativity  
*What is novel or unique in your approach?*  

#### 2.1 Intent-aware multi-model routing

Instead of training a single monolithic policy that covers all sushi types, we:

- Convert user speech to text using Whisper.
- Send the transcription to the Gemini API to:
  - Correct recognition errors.
  - Interpret vague or indirect expressions (e.g., “the red one”, “vegan option”, “for kids”).
  - Infer the intended menu item from context.
- Map the interpreted intent to one of several **discrete skills**:
  - `tuna`, `egg`, `tempura`, `cucumber_roll`, `greentea_cup`
- Automatically select and load the corresponding **Hugging Face policy model**:


This design lets the user give **natural, sometimes ambiguous voice commands** without knowing the exact menu names, while the system handles the mapping to the correct robot skill.

#### 2.2 Modular “skill-per-menu” design

Compared to “one giant model that does everything,” our approach:

- Assigns **one dataset + one policy model per menu item**.
- Makes it easy to:
  - Add new dishes: collect demos → train a new policy → add one routing rule.
  - Debug and retrain: only the failing menu’s model needs to be fixed.
- Keeps each policy’s training data focused on a single behavior, which simplifies data collection and improves consistency.

#### 2.3 Natural voice-first interface with GUI / CLI

- A Tkinter-based GUI provides a **“push-to-talk”** style interface:
  - The user clicks a button, speaks, and sees:
    - Interpreted order menu texts
    - Interpreted order images
- This combination makes the system both **demo-friendly for non-technical users** and **easy to debug for developers**.

---

### 3. Technical Implementations  

#### 3.1 Teleoperation / Dataset Capture  

- **Robot & Sensors**
  - Robot: SO-101 follower arm (`/dev/ttyACM0`)
  - Cameras:
    - Top camera (overhead view, USB device index like `/dev/videoX`, 640×480)
    - Wrist camera (close-up hand view, 640×480)
- **Teleoperation**
  - We used `lerobot-record` with the `so101_follower` environment.
  - The operator physically guided the SO-101 arm (kinesthetic teaching) to demonstrate:
    - Placing tuna/egg/tempura on rice and then on a plate.
    - Picking and serving cucumber rolls directly to a plate.
    - Placeing the greentea cup right next to the saucer.
  - We carefully designed the camera viewpoints so that:
    - The target objects (rice, toppings, plate) are clearly visible.
    - The workspace is visually simple and consistent.
- **Visual isolation**
  - We added simple blinds and arranged the background to **exclude unnecessary visual clutter**, making it easier for the model to learn the relevant parts of the scene.
- **Dataset contents**
  - Each episode records:
    - Top camera image sequence (`observation.images.top`)
    - Wrist camera images (`observation.images.wrist`)
    - Robot state (joint positions and gripper state, `observation.state`)
    - Actions (joint commands + gripper commands)
  - Datasets are stored in LeRobot’s standard format and uploaded to Hugging Face Datasets.

> *Image/video of teleoperation or dataset capture will be linked in the Additional Links section.*

---

#### 3.2 Training  

- **Policy architecture**
  - Framework: LeRobot
  - Policy type: `act` (Action Chunking Transformer)
  - Vision backbone: `resnet18` with ImageNet pretraining
  - Inputs:
    - `observation.images.top` (3×480×640)
    - `observation.images.wrist` (3×480×640)
    - `observation.state` (6D)
  - Output:
    - `action` (6D continuous joint-space actions)

- **Training procedure**
  - For each menu (tuna, egg, tempura, cucumber roll, greentea cup):
    - Train an independent ACT policy using the corresponding dataset.
    - Use batch size 64 and train for **around 25,000–30,000 steps** per model.
  - Use Weights & Biases (`wandb`) to:
    - Monitor training loss curves.
    - Compare different runs.
    - Decide when to stop training.
  - For some models (e.g., egg sushi), we:
    - Started from an existing checkpoint (`pretrained_model`).
    - Applied additional fine-tuning with `--resume=true` to stabilize trajectories and improve success rates.

- **Deployment**
  - After training, each policy is pushed to Hugging Face via:
    - `--policy.push_to_hub=true`
    - `--policy.repo_id=HankLL/ServeXxxSushi`
  - This makes each skill easily reusable and shareable.

---

#### 3.3 Inference  

The runtime system is structured as an end-to-end pipeline:

1. **Speech input & transcription**
   - The GUI or CLI triggers recording via Python.
   - Audio is transcribed by the Whisper library into text.

2. **Language understanding & routing**
   - The Whisper transcription is sent to the Gemini API, which:
     - Corrects recognition mistakes.
     - Interprets indirect phrases (e.g., “the red one”, “something vegan”).
     - Infers the user’s intended menu item.
   - The inferred menu name is mapped to a skill:
     - `tuna`, `egg`, `tempura`, `cucumber_roll`, or 'greentea cup'.

3. **Model selection & loading**
   - The router selects the corresponding Hugging Face policy:
     - e.g., `HankLL/ServeEggSushi/pretrained_model`.
   - The model is loaded via LeRobot’s `from_pretrained`.

4. **Robot control**
   - SO-101 provides:
     - Real-time images from top and wrist cameras.
     - Current joint states.
   - The ACT policy takes these observations and outputs an action sequence.
   - Actions are sent to the robot at a fixed control rate, executing the serving motion until the task is completed.

5. **User feedback**
   - The GUI displays:
     - Interpreted order menu texts
     - Interpreted order images
   - This transparency helps users understand how the system interpreted their speech and which skill is being used.

> *Image/video of inference and evaluation will be linked in the Additional Links section.*

---

### 4. Ease of Use  

#### 4.1 Generalizability

- The core architecture:
  - `Voice → Text → Task representation (skill name) → Robot policy`
- This pattern is not limited to sushi; it can be reused for:
  - Simple assembly tasks
  - Item sorting and placement
  - Other food preparation and serving scenarios
- To add a new task:
  1. Collect teleoperation demos with SO-101.
  2. Train a new ACT policy with LeRobot.
  3. Add a new skill name + routing rule in the Gemini-based mapping.

#### 4.2 Flexibility and adaptability

- Device-dependent parameters (microphone ID, camera indices, serial port, resolutions) are:
  - Externalized as configuration in `sushi_voice_master.py` / `sushi_voice_master_ui.py`.
  - Easily adjusted for different hardware setups and environments.
- We have validated the system on:
  - Ubuntu 24.04
  - SO-101 robot arm
  - Two USB cameras (top + wrist)
- Adding a new menu item (task) only requires:
  - Training a new policy on its dataset.
  - Adding the model and label to the menu list and routing logic.

#### 4.3 Commands and interfaces to control the robot

- *Types of commands or interfaces needed to control the robot*
    1. **Clone the repository**
    ```bash
    git clone https://github.com/Hank-LL/AMD_Robotics_Hackathon_2025_Team27.git
    cd AMD_Robotics_Hackathon_2025_Team27/mission2
    ```

    2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

    3. **Set environment variable for Gemini API**
    ```bash
    export GEMINI_API_KEY="your-gemini-api-key"
    ```

    4. **Check device configuration**
    
    Verify your microphone and camera device IDs:
    ```bash
    # List audio devices
    python -c "import sounddevice as sd; print(sd.query_devices())"
    
    # List video devices
    ls /dev/video*
    ```
    
    Update device IDs in `code/sushi_voice_master_ui.py` if needed:
    - `MIC_DEVICE`: Microphone device ID
    - Camera indices in `cameras` parameter


    5. **Run the application**
    
    **GUI Version (Recommended):**
    ```bash
    cd code
    python sushi_voice_master_ui.py
    ```
    
    **CLI Version:**
    ```bash
    cd code
    python sushi_voice_master.py
    ```

## Additional Links

Note: The robot switches models depending on the requested sushi item, so each menu entry has a dedicated dataset and model.

### Link to a video of your robot performing the task

- [recording](https://youtu.be/fsniYRbwewI?si=UBAtkGbdxnlD5s4B)
- [inference](https://youtube.com/shorts/wll964TdrcQ?si=rXTlZOPqFFjENat8)

### URL of your dataset in Hugging Face
- [ServeEggSushi](https://huggingface.co/datasets/HankLL/ServeEggSushi)
- [ServeTunaSushi](https://huggingface.co/datasets/HankLL/ServeTunaSushi)
- [ServeCucumberRoll](https://huggingface.co/datasets/HankLL/ServeCucumberRoll)
- [ServeTempuraSushi](https://huggingface.co/datasets/HankLL/ServeTempuraSushi)

### URL of your model in Hugging Face
- [ServeEggSushi](https://huggingface.co/HankLL/ServeEggSushi)
- [ServeTunaSushi](https://huggingface.co/HankLL/ServeTunaSushi)
- [ServeCucumberRoll](https://huggingface.co/HankLL/ServeCucumberRoll)
- [ServeTempuraSushi](https://huggingface.co/HankLL/ServeTempuraSushi)

## System Structure

```mermaid
 graph TD
    %% Define Styles
    classDef input fill:#f9f,stroke:#333,stroke-width:2px;
    classDef process fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef logic fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef storage fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    %% Nodes
    User([User / Microphone]):::input
    Whisper[Whisper Library]:::process
    Gemini{{Gemini API}}:::logic
    HF_Hub[Hugging Face Hub]:::storage
    TargetModel[Target AI Model]:::input

    %% Flow
    User -->|1. Voice Order| Whisper
    
    subgraph "Perception & Reasoning"
        Whisper -->|2. Transcribed Text| Gemini
        
        %% Note for Gemini's role
        note_g[Context Awareness &<br/>Error Correction] -.-> Gemini
    end

    subgraph "Execution Pipeline"
        Gemini -->|3. Select Appropriate Model| HF_Hub
        HF_Hub -->|4. Load| TargetModel
    end
```
