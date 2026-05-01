import asyncio, os, re, json, random, ast
from autogen_agentchat.agents import AssistantAgent 
from autogen_agentchat.teams import RoundRobinGroupChat 
from autogen_agentchat.conditions import TextMentionTermination 
from autogen_agentchat.ui import Console 
from autogen_ext.models.openai import OpenAIChatCompletionClient 

from data_base_profiles import load_profile, upsert_profile, list_profiles #for the user profile 
import streamlit as st #for the UI interface 
import whisper #for the use of auto_text_recognition 
from deep_translator import GoogleTranslator #for the use of machine_translator 
from elevenlabs.client import ElevenLabs #for text_ to_speech 
from elevenlabs import VoiceSettings 
from st_audiorec import st_audiorec #for recording audio in streamlit 
from constraint import Problem #for constraints
from typing import Optional,Set #for optional input and specifying the type of input expected


ELEVENLABS_API_KEY = "YOUR ELEVENLABS API KEY" 
OPENROUTER_API_KEYS = os.getenv("OPENROUTER_API_KEY", "YOUR OPENROUTER API KEY") 

model_client = OpenAIChatCompletionClient( 
    model="alibaba/tongyi-deepresearch-30b-a3b:free",   
    api_key=OPENROUTER_API_KEYS,
    base_url="https://openrouter.ai/api/v1", 
    model_info={ 
            "vision": False, 
            "function_calling": True, 
            "json_output": False, 
            "family": "unknown", 
            "structured_output": True, 
            "max_tokens": 2000
    } 
) 

def user_profile(user_id: str): 
    profile = load_profile(user_id) 
    return {"profile": profile} 


languages_available = ["es", "en", "pt", "fr", "de", "it", "ja", "ru", "zh-CN"]
client = ElevenLabs(api_key="sk_20075e7bd8ea62d8ad42f37429a6dfbae60245e55f718879")
voices = client.voices.get_all()
voice = [v.name for v in voices.voices] 
voice_gender = ["Male","Female"]


def csp(languages_available, voice): 
    source = st.session_state.get("source_language")
    target = st.session_state.get("target_language")
    voice_gen = st.session_state.get("voice_gen")
    lang_restrictions = [("ja","es"),("ru","fr"),("pt","zh-CN")]
    voice_restrictions = [
        ("es","Laura"), ("es","Daniel"), ("en","Sarah"), ("en","Will"),
        ("pt","Jessica"), ("pt","Brian"), ("fr","Clyde"), ("fr","Alice"),
        ("de","Roger"), ("de","George"), ("it","Matilda"), ("it","Eric"),
        ("ja","Charlie"), ("ja","Lily"), ("ru","Harry"), ("ru","River"),
        ("zh-CN","Callum"), ("zh-CN","Bill")]
    voice_gen_restrictions = [
        ("Female","Laura"), ("Male","Daniel"), ("Female","Sarah"), ("Male","Will"),
        ("Female","Jessica"), ("Male","Brian"), ("Male","Clyde"), ("Female","Alice"),
        ("Male","Roger"), ("Male","George"), ("Female","Matilda"), ("Male","Eric"),
        ("Male","Charlie"), ("Female","Lily"), ("Male","Harry"), ("Female","River"),
        ("Male","Callum"), ("Male","Bill")]
    problem = Problem()
    problem.addVariable("source", languages_available)
    problem.addVariable("target", languages_available)
    problem.addVariable("voice",voice)
    problem.addVariable("voice_gen",voice_gender)

    problem.addConstraint(lambda s, t: s != t, ("source", "target"))
    problem.addConstraint(lambda s, t: (s, t) not in lang_restrictions and (t,s) not in lang_restrictions, ("source", "target"))
    problem.addConstraint(lambda t,v: (t,v) in voice_restrictions, ("target","voice"))
    problem.addConstraint(lambda g,v: (g,v) in voice_gen_restrictions, ("voice_gen","voice"))

    if source == target:
        return -2
    
    solutions = problem.getSolutions()
    solution = [s for s in solutions if s['source'] == source and s['target'] == target and s['voice_gen'] == voice_gen]
    if len(solution)>0:
        chosen_solution = random.choice(solution)
        return chosen_solution
    else:
        return -1
    
lang_graph = {
    "es": ["en","pt","fr","de","it","ru","zh-CN"],
    "en": ["ja","pt","zh-CN","de","it","es","ru","zh-CN"],
    "pt": ["es","en","fr","de","it","ja","ru"],
    "fr": ["es", "en", "pt", "de", "it", "ja", "zh-CN"],
    "de": ["es", "en", "pt", "fr", "it", "ja", "ru", "zh-CN"],
    "it": ["es", "en", "pt", "fr", "de", "ja", "ru", "zh-CN"],
    "ja": [ "zh-CN", "en", "fr", "de", "it", "ru", "pt"],
    "ru":["es", "en", "pt", "de","it", "ja", "ru", "zh-CN"],
    "zh-CN": ["es", "en", "fr", "de", "it", "ja", "ru"]
}


def dfs(lang_graph: dict, source: str, target: str, visited: Optional[Set[str]] = None) -> dict:
    if visited is None:
        visited = set()
    
    if source == target:
        return {"road": [source]}
    
    visited.add(source)
    
    for neighbor in lang_graph.get(source, []):
        if neighbor not in visited:
            result = dfs(lang_graph, neighbor, target, visited.copy())
            if result["road"] is not None:
                return {"road": [source] + result["road"]}
    
    return {"road": None}

def translate_along_path(user_id: str, transcript: str, road: list) -> dict:
    
    if not road or len(road) < 2:
        profile = load_profile(user_id)
        return {
            "transcript": transcript, 
            "detected_language": profile["source_language"]
        }
    
    profile = load_profile(user_id)
    #original_target = profile["target_language"]
    text = transcript
    
    current_text = text
    for i in range(len(road) - 2):  #it stops at the second-to-last one
        try:
            current_text = GoogleTranslator(
                source=road[i], 
                target=road[i + 1]
            ).translate(current_text)
            print(f"Traduciendo {road[i]} -> {road[i+1]}: {current_text}")
        except Exception as e:
            st.error(f"Error en paso {road[i]}->{road[i+1]}: {str(e)}")
            break

    target_language = road[-2] 
    
    return {
        "transcript": current_text,
        "detected_language": target_language
    }

def dfs_translate(user_id: str, transcript: str):
    
    profile = load_profile(user_id)
    source = profile["source_language"]
    target = profile["target_language"]
    
    lang_restrictions = [("ja","es"),("ru","fr"),("pt","zh-CN"),("es","ja"),("fr","ru"),("zh-CN","pt")]
    if (source, target) in lang_restrictions:
        result = dfs(lang_graph, source, target)
        if result["road"]:
            return translate_along_path(user_id, transcript, result["road"])
        else:
            return {"transcript": transcript, "detected_language": target}
    else:
            return {"transcript": transcript, "detected_language": source}
    
def auto_text_recognition(audio_file: str):  
    try:  
        model = whisper.load_model("base")  
        result = model.transcribe(audio_file, fp16 = False)   
        transcription = result["text"]  
        return {
            "transcript": transcription,
            "detected_language": result.get("language", None)
        }
    except Exception as e:  
        st.error(f"Error during transcription: {str(e)}") 

def latency(text: str, profile: dict): 
    max_latency = profile.get("max_latency_ms", 1500) 
    text_len = len(text) 
    if text_len < 80 and max_latency <= 1500: 
        return {"mode": "fast", "time_left_ms": max_latency} 
    else: 
        return {"mode": "quality", "time_left_ms": max_latency} 

def machine_translation(user_id: str, text:str): 
    try: 
        profile = load_profile(user_id)   
        translation = GoogleTranslator(source=profile["source_language"], target=profile["target_language"]).translate(text) 
        return {"translated_text": translation}
    except Exception as e:  
        st.error(f"Error during translation: {str(e)}") 

def text_to_speech(text_to_convert: str) -> dict: 
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    voices = client.voices.get_all()
    voice = [v.name for v in voices.voices]
    languages_available = ["es", "en", "pt", "fr", "de", "it", "ja", "ru", "zh-CN"]
    c = csp(languages_available, voice)
    if isinstance(c, dict):
        f_voice = c["voice"]
    else:
        target = st.session_state.get("target_language")
        voice_gen = st.session_state.get("voice_gen")
        voice_restrictions = [
        ("es","Laura"), ("es","Daniel"), ("en","Sarah"), ("en","Will"),
        ("pt","Jessica"), ("pt","Brian"), ("fr","Clyde"), ("fr","Alice"),
        ("de","Roger"), ("de","Matilda"),("de","George"), ("it","Matilda"), ("it","Eric"),
        ("ja","Charlie"), ("ja","Lily"), ("ru","Harry"), ("ru","River"),
        ("zh-CN","Callum"), ("zh-CN","Bill"), ("zh-CN","Jessica")]
        voice_gen_restrictions = [
        ("Female","Laura"), ("Male","Daniel"), ("Female","Sarah"), ("Male","Will"),
        ("Female","Jessica"), ("Male","Brian"), ("Male","Clyde"), ("Female","Alice"),
        ("Male","Roger"), ("Male","George"), ("Female","Matilda"), ("Male","Eric"),
        ("Male","Charlie"), ("Female","Lily"), ("Male","Harry"), ("Female","River"),
        ("Male","Callum"), ("Male","Bill"),("Male","Liam"),("Male","Chris"),("Male","Adam")]
        if target!=None and voice_gen!=None:
            v1 = [v for (lang, v) in voice_restrictions if lang == target]
            v2 = [v for (g, v) in voice_gen_restrictions if g == voice_gen]
            f_voice = [v for v in v1 if v in v2]
    #print(f_voice)
    voices = client.voices.get_all()
    voice_id = [v.voice_id for v in voices.voices if v.name in f_voice][0]
    #print(voice_id)
    try:  
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY) 
        response = client.text_to_speech.convert( 
            voice_id=voice_id,  
            optimize_streaming_latency="0", 
            output_format="mp3_22050_32", 
            text=text_to_convert, 
            model_id="eleven_turbo_v2",   
            voice_settings=VoiceSettings( 
                stability=0.0, 
                similarity_boost=1.0, 
                style=0.0, 
                use_speaker_boost=True, 
            ), 
        ) 
        save_file_path = "audios/traduc.mp3" 

        with open(save_file_path, "wb") as audio: #we open the file in text and binary format 
            for chunk in response: 
                if chunk: 
                    audio.write(chunk) 
        
        return {"audio_path": save_file_path}  
    except Exception as e: 
        st.error(f"Error during audio conversion: {str(e)}") 

async def run_ai_live_translator(claim: str): 
    profile_agent = AssistantAgent( 
        name="profile_agent", 
        model_client=model_client, 
        tools=[user_profile], 
        system_message=( 
            "Role: Profile Agent.\n" 
            "You load the user profile from the tool user_profile().\n" 
            "Return ONLY JSON: {\"profile\": {...}}" 
        ) 
    ) 

    asr_agent = AssistantAgent( 
        name="asr_agent", 
        model_client=model_client, 
        tools=[auto_text_recognition], 
        system_message=( 
            "Role: ASR Agent.\n" 
            "You receive an audio path and MUST call auto_text_recognition(audio_file) to get transcript and detected_language.\n" 
            "Return ONLY JSON: {\"transcript\": \"...\", \"detected_language\": \"...\"}" 
        ) 
    ) 

    latency_agent = AssistantAgent( 
        name="latency_agent", 
        model_client=model_client, 
        tools=[latency], 
        system_message=( 
            "Role: Latency Manager.\n" 
            "You receive the transcript and the profile and must call latency(text: str, profile: dict).\n" 
            "You pass the information to the mt_agent.\n" 
            "Return ONLY JSON: {\"mode\": \"fast|quality\", \"time_left_ms\": <int>}" 
        ) 
    ) 

    dfs_agent = AssistantAgent( 
        name="dfs_agent", 
        model_client=model_client, 
        tools=[dfs_translate], 
        system_message=(  
            "Role: DFS Agent.\n"
            "You receive the transcript and the profile.\n"
            "You MUST call the dfs_translate(user_id: str, transcript: str)\n" 
            "Return ONLY JSON: {\"transcript\": \"...\", \"detected_language\": \"...\"}" 
        ) 
    ) 

    mt_agent = AssistantAgent( 
        name="mt_agent", 
        model_client=model_client, 
        tools=[machine_translation], 
        system_message=( 
            "Role: MT Agent.\n" 
            "If latency_agent indicates the mode fast, translate the transcript into the target language using machine_translation(user_id: str).\n" 
            "If latency_agent indicates the mode quality, translate the transcript into the target language using your knowledge and carefully.\n" 
            "Return ONLY JSON: {\"translated_text\": \"...\"}" 
        ) 
    ) 

    summarizer_agent = AssistantAgent( 
        name="summarizer_agent", 
        model_client=model_client, 
        system_message=( 
            "Role: Summarizer Agent.\n" 
            "You receive an already translated text.\n" 
            "Summarize it in the same language in 1-2 sentences ONLY if it has more than 150 letters, if it has less DON´T make a summary.\n" 
            "Return ONLY JSON: {\"summary\": \"...\"}" 
        ) 
    ) 

    tts_agent = AssistantAgent( 
        name="tts_agent", 
        model_client=model_client, 
        tools=[text_to_speech], 
        system_message=( 
            "Role: TTS Agent.\n" 
            "Generate speech from the translated text and from the summarized using the tool text_to_speech(text_to_convert:str).\n"  
            "If the summary is empty, generate speech from the translated text only."
            "AFTER the tool call finishes, you MUST always send a final message.\n"
            "Return ONLY JSON starting with TRANSLATION:"
            "TRANSLATION {\"audio_path\": \"...\", \"text\": \"...\", \"summary\": \"...\"}"
            "Do NOT skip this final message.\n"
        ) 
    ) 

    team = RoundRobinGroupChat( 
        [profile_agent, asr_agent, latency_agent, dfs_agent, mt_agent, summarizer_agent, tts_agent], 
        max_turns=7, 
        termination_condition=TextMentionTermination("TRANSLATION") 
    ) 

    result = await Console(team.run_stream(task=claim)) 
    await model_client.close() 
    return result 

def main(): 
    st.set_page_config("AI Live Translator", layout="wide") 

    if "current_user" not in st.session_state: 
        st.session_state["current_user"] = "" 
    if "messages" not in st.session_state: 
        st.session_state["messages"] = [] 

    st.sidebar.header("User Profile") 

    users = list_profiles() 

    selected_user = st.sidebar.selectbox( 
        "Choose existing user", 
        ["-- new --"] + users, 
        index=0 
    ) 

    if selected_user != "-- new --": 
        user_id_input = selected_user 
    else: 
        user_id_input = st.sidebar.text_input( 
            "New user ID", 
            value=st.session_state.get("current_user", "") 
        ) 

    if user_id_input: 
        existing = load_profile(user_id_input) 
    else: 
        existing = None 

    languages_available = ["es", "en", "pt", "fr", "de", "it", "ja", "ru", "zh-CN"] 

    source = st.sidebar.selectbox( 
        "Source language", 
        languages_available, 
        index=0 if not existing else languages_available.index(existing["source_language"]) 
    ) 
    st.session_state["source_language"] = source

    target = st.sidebar.selectbox( 
        "Target language", 
        languages_available, 
        index=1 if not existing else languages_available.index(existing["target_language"]) 
    ) 
    st.session_state["target_language"] = target

    voice_gen = st.sidebar.selectbox( 
        "Voice gender", 
        voice_gender, 
        index=0 if not existing else voice_gender.index(existing["voice_gen"]) 
    ) 
    st.session_state["voice_gen"] = voice_gen

    constraint = csp(languages_available,voice)   
    
    if constraint == -1:
        st.warning("⚠️ This translation pair poses a risk of reduced translation fidelity")
        #st.warning("Verify the selected languages")
    elif constraint == -2:
        st.warning("⚠️ The user's request was not completed, the source and target languages are the same.")

    
    register = st.sidebar.radio( 
        "Register", 
        ["formal", "informal"], 
        index=0 if not existing else (0 if existing["register"] == "formal" else 1) 
    ) 

    latency_ms = st.sidebar.slider( 
        "Max latency (ms) \nFast (less than 1500) \nQuality (more than 1500)", 
        300, 3000, 
        1500 if not existing else existing["max_latency_ms"], 
        step=100 
    ) 

    if st.sidebar.button("Save / Update"): 
        upsert_profile(user_id_input, source, target, voice_gen, register, latency_ms) 
        st.session_state["current_user"] = user_id_input 
        st.sidebar.success(f"Profile saved for {user_id_input}") 

    st.header("AI Live Translator", divider="red") 
    st.subheader(":gray[_by Carlos Lomelín and Sebastián Garmendia_]") 
    st.write(f"Welcome, **{st.session_state['current_user'] or 'invitad@'}**") 

    for msg in st.session_state["messages"]:
        with st.chat_message(msg.get("role","assistant")):
            st.write(msg.get("content",""))
            ab = msg.get("audio_bytes", b"")
            ap = msg.get("audio", "")
            if ab:
                st.audio(ab, format="audio/mp3")
            elif ap and os.path.isfile(ap) and os.path.getsize(ap) > 0:
                st.audio(ap, format="audio/mp3") 

    st.markdown("Recording") 
    audio_bytes = st_audiorec() 

    if audio_bytes is not None: 
        st.audio(audio_bytes, format="audio/wav") 
        st.success("Recorded Audio") 

    if constraint != -2:
        if st.button("Translate this audio"): 
            os.makedirs("audios", exist_ok=True) 
            input_path = os.path.join("audios", "input.wav") 
            with open(input_path, "wb") as f: 
                f.write(audio_bytes) 

            user_id = st.session_state.get("current_user") or user_id_input or "invitado"
            claim = (
                f"User '{user_id}' sent audio at path '{input_path}'. "
                "Run the full agent pipeline (profile -> ASR -> latency -> DFs -> MT -> summarizer -> TTS) "
                "and answer according to the TTS Agent instructions."
            )
        
            result = asyncio.run(run_ai_live_translator(claim))

            def _to_text(c):
                if isinstance(c, list):
                    return "".join([p.get("text", "") for p in c if isinstance(p, dict)])
                return c if isinstance(c, str) else ""

            msgs = getattr(result, "messages", []) or []

            payload = ""
            for m in reversed(msgs):
                content = _to_text(getattr(m, "content", ""))
                if "TRANSLATION" in content:
                    payload = content
                    break

            translated_text, summary, tts_path = "", "", ""

            if payload:
                m = re.search(r"TRANSLATION\s+({.*})", payload, re.S)
                if m:
                    raw = m.group(1).strip()
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        data = ast.literal_eval(raw)

                    translated_text = (data.get("text") or "").strip()
                    summary = (data.get("summary") or "").strip()
                    #tts_path = (data.get("audio_path") or "").strip()

            if not translated_text:
                for m in reversed(msgs):
                    content = _to_text(getattr(m, "content", ""))
                    if '"translated_text"' in content or "'translated_text'" in content:
                        j = re.search(r"({.*})", content, re.S)
                        if not j:
                            continue
                        raw = j.group(1).strip()
                        try:
                            d = json.loads(raw)
                        except json.JSONDecodeError:
                            d = ast.literal_eval(raw)
                        translated_text = (d.get("translated_text") or "").strip()
                        break

            if not summary:
                for m in reversed(msgs):
                    content = _to_text(getattr(m, "content", ""))
                    if '"summary"' in content or "'summary'" in content:
                        j = re.search(r"({.*})", content, re.S)
                        if not j:
                            continue
                        raw = j.group(1).strip()
                        try:
                            d = json.loads(raw)
                        except json.JSONDecodeError:
                            d = ast.literal_eval(raw)
                        summary = (d.get("summary") or "").strip()
                        if summary:
                            break

            audio_mp3_bytes = b""
            if translated_text:
                tts_res = text_to_speech(translated_text) or {}
                tts_path = (tts_res.get("audio_path") or "").strip()

            if tts_path and os.path.isfile(tts_path) and os.path.getsize(tts_path) > 0:
                with open(tts_path, "rb") as f:
                    audio_mp3_bytes = f.read()

            content_text = f"Translation: {translated_text}" if translated_text else "Translation no available"
            if summary:
                content_text += f"\n\nSummary: {summary}"

            st.session_state["messages"].append({
                "role": "assistant",
                "content": content_text,
                "audio": tts_path,
                "audio_bytes": audio_mp3_bytes
            })
            st.rerun()


if __name__ == "__main__": #streamlit dont really need this (only when do we want to run like a normal script) 
   main()