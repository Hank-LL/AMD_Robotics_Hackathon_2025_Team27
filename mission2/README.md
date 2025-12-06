## Task Summary

- Overview
    - Sushi Chef Task
- Flow
    1. Receive sushi orders via microphone (Tuna, Egg, Tempura, Cucumber Roll, Tea Cup)
    2. Serve dishes according to the order
        1. Tuna, Tempura, Egg:
            1. Place on sushi rice and serve on a plate
        2. Cucumber Roll:
            1. Serve directly on a plate
        3. Tea Cup:
            1. Serve directly next to the plate

## Input Information

- overhead camera(640✕480)
- wrist camera(640✕480)

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