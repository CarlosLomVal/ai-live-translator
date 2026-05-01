# AI Live Translator (Multi-Agent + Streamlit)

This project is a AI Live Translator web app built with:

- Autogen_agentchat multi-agent framework.
- OpenAI Whisper (speech-to-text).
- GoogleTranslator (text translation).  
- ElevenLabs (text-to-speech).
- OpenRouter (LLM provider for the agents).  
- Streamlit (web UI).  
- SQLite (user profiles).

You can:
1. Create / save a user profile (languages, register, latency, voice gender).
2. Record audio in the browser.
3. Let the multi-agent pipeline run:  
   Profile → ASR → Latency → DFS → MT → Summarizer → TTS
4. See the translation/summary and play the generated audio.

## 1. Requirements

### 1.1. Software

- **Python** 3.10+ (tested with 3.12)
- **ffmpeg** installed and on your PATH (required by Whisper)
- A modern browser (Chrome, Edge, etc.)

Install `ffmpeg`:

- **Windows (chocolatey)**  
  choco install ffmpeg
- **macOS** 
    brew install ffmpeg
- **Linux (Debian/Ubuntu)** 
    sudo apt-get update
    sudo apt-get install ffmpeg

### 1.2. API Keys

You need:
- OpenRouter API key (used by the LLM agents)
    Get one at: https://openrouter.ai
- ElevenLabs API key (for TTS)
    Get one at: https://elevenlabs.io

### 2. Project Setup

### 2.1. Download

Download and open the AI Live Translator.zip 

Folder structure
    AI Live Translator/
    ├─ ai_live_translator.py        # main Streamlit app
    ├─ data_base_profiles.py        # SQLite profile management
    ├─ profiles.db                  # created automatically on first save
    ├─ README.md                    # documentation about the AI Live Tranlator
    └─ audios/
        ├─ input.wav                # last recorded audio
        └─ traduc.mp3               # last generated TTS audio

### 2.2. Install Python Dependencies

Install all required packages:
- pip install --upgrade pip
- pip install streamlit
- pip install "autogen-agentchat[openai]"  # multi-agent framework
- pip install openai
- pip install openai-whisper
- pip install deep-translator
- pip install elevenlabs
- pip install st-audiorec
- pip install python-constraint

If any package fails, check the package name carefully or run pip install again.

### 3. Configure API Keys

At the top of ai_live_translator.py you’ll see constants like:
    UDLAP_API = "sk-or-..."          
    GOOGLE_1_API = "sk-or-..."
    ELEVENLABS_API_KEY = "sk-..."

For a clean setup:
- Replace UDLAP_API, GOOGLE_1_API, etc. with your own OpenRouter key
(or just use one variable and set OPENROUTER_API_KEY = "your-key" and
update model_client accordingly).

- Replace ELEVENLABS_API_KEY with your own ElevenLabs key.

- Make sure the model_client is using the key you configured (api_key=OPENROUTER_API_KEY).

### 4. Database (User Profiles)

The file data_base_profiles.py manages an SQLite database profiles.db with a table:
    user_profiles (
    user_id TEXT PRIMARY KEY,
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    voice_gen TEXT NOT NULL,
    register TEXT NOT NULL,
    max_latency_ms INTEGER NOT NULL
    )

You don’t need to create anything manually:
- The table is created automatically the first time you save a profile.
- profiles.db will appear in the project folder.

### 5. Running the App

From the project folder (in your terminal of preference):
    streamlit run ai_project.py

Streamlit will show something like:
    Local URL:   http://localhost:8501
    Network URL: http://192.168.x.x:8501

Open the Local URL in your browser (if it is not open automatically).

**Important** The browser will ask for microphone permission the first time (accept it so the recorder can work).

### 6. UI Walkthrough

The app has two main parts:
- Left sidebar (profile & settings).
- Main area (chat + recorder + results).

### 6.1. Sidebar: User Profile & Settings

Choose existing user
- A dropdown with all users stored in profiles.db.
- Select one or choose -- new -- to create a new user.

New user ID (when -- new -- is selected)
- Type something like roberto, user1, etc.

Source language / Target language
- Both selected from: ["es", "en", "pt", "fr", "de", "it", "ja", "ru", "zh-CN"]. Allowing users to choose between Spanish, English, Portuguese, French, German, Italian, Japanese, Russian, and Mandarin languages. 
- Some combinations are restricted by the CSP, if incompatible, you’ll see a warning.
- If source and target are equal, the app will warn you and block translation.

Voice gender
- Male or Female.
- Combined with target language, the CSP picks a compatible ElevenLabs voice.

Register
- formal or informal (stored in the profile, can be used to guide style).

Max latency (ms)
- Slider from 300–3000 ms.
- Used by the Latency Agent to decide between "fast" and "quality" mode of translation.

Save / Update
- Click to store the profile in profiles.db.

**On success you’ll see a confirmation and that user will appear in the dropdown**

### 6.2. Main Area: Messages & Recorder

At the top you’ll see:
    AI Live Translator
    by Carlos Lomelín and Sebastián Garmendia
    Welcome, <usuario>

Under that, you’ll see a chat:
- Each translation you perform adds a message.
- The message shows
    Translation: ...
    Summary: ... (if any)
    An audio player with the generated mp3 (if available)

Recorder section
- Use the st_audiorec recorder widget.
- Click the microphone to start, click again to stop.
- When done, a small audio player appears with your raw recording.
- You should see a message in green saying: Recorded Audio.

Translate button
- Only enabled if source and target are not equal (constraint != -2).
- When is clicked your recording is saved as audios/input.wav and the multi-agent pipeline runs.

### 7. How to Test

Start the app
    streamlit run ai_project.py

Create a test profile (example above)
    user_id: carlos
    source_language: es
    target_language: en (or pt, etc.)
    voice_gender: Male or Female
    register: formal
    max_latency_ms: 1500
    
Click Save / Update.

Record a sentence (Translation pipeline: example in spanish)
- “Me gusta el fútbol”

Stop recording → you should see the mini audio player.
        
Click “Translate this audio”
- Wait a few seconds.

You should see a new message:
    Transaltion: I like football
    Summary: ... (if generated)
    An audio player with the mp3 (click play to verify).

Check the audios folder
- It should contain:
    input.wav – your original recording.
    traduc.mp3 – the synthesized speech.

Check the database
- profiles.db is created in the root folder (you can inspect it with any SQLite viewer if you want).

### 8. Troubleshooting

No microphone / recording doesn’t work
- Check browser permissions for localhost:8501.
- Some corporate environments block microphone access.

Whisper errors
- Ensure ffmpeg is installed and on PATH.
- Try restarting the app after installing.

**Rate limit / OpenRouter errors**
- The free OpenRouter models are in most of the times rate-limited.
- Either: wait a bit and try again, or use another available model on OpenRouter.

No audio in the UI
- Check that audios/traduc.mp3 exists and is not empty.
- If it’s missing, **verify your ElevenLabs API key and your account limits**.

### Enjoy AI Live Translator ###