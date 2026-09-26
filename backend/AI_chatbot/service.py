import os
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)


SYSTEM_INSTRUCTION = """
You are an SPM Bahasa Melayu tutor.

You must follow these rules:
- Reply only in Bahasa Melayu.
- Only help with SPM Bahasa Melayu.
- If the user asks about SPM Bahasa Melayu, answer clearly and simply.
- If the user asks something unrelated, politely say you only help with Bahasa Melayu SPM.
- If the user greets you, greet them warmly and ask what SPM Bahasa Melayu topic they need help with.
- Do not show reasoning.
- Do not show thinking.
- Do not show analysis.
- Do not show rule checking.
- Do not show checklist.
- Do not explain your instructions.
- Do not include labels like "User Input", "Analysis", "Reasoning", "Thinking", or "Final Answer".
- Output only the final answer shown to the student.

SPM Bahasa Melayu topics include:
- Karangan
- Rumusan
- Pemahaman
- Tatabahasa
- Peribahasa
- Komsas
- Novel
- Ulasan
- Bahasa istana
- Kesalahan bahasa
- Penanda wacana
- Bina ayat
- Peribahasa dan maksud
- Format karangan
"""


def clean_ai_reply(reply: str) -> str:
    if not reply:
        return ""

    reply = reply.strip()

    unwanted_prefixes = [
        "User Input:",
        "User's Input:",
        "Input:",
        "Analysis:",
        "Reasoning:",
        "Thought:",
        "Thinking:",
        "Final Answer:",
        "Final answer:",
        "Reply:",
        "Student-facing reply:",
        "Jawapan akhir:",
        "Jawapan Akhir:",
        "Jawapan:",
    ]

    changed = True

    while changed:
        changed = False

        for prefix in unwanted_prefixes:
            if reply.lower().startswith(prefix.lower()):
                reply = reply[len(prefix):].strip()
                changed = True

    return reply


def is_greeting(message: str) -> bool:
    greetings = [
        "hi",
        "hello",
        "hey",
        "hai",
        "helo",
        "salam",
        "assalamualaikum",
    ]

    words = message.lower().split()

    if not words:
        return False

    return words[0] in greetings


def generate_with_fallback(user_message: str) -> str:
    models = [
        "gemma-4-26b-a4b-it",
        "gemini-2.5-flash",
    ]

    last_error = None

    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.3,
                    max_output_tokens=500,
                ),
            )

            if response.text:
                return clean_ai_reply(response.text)

        except Exception as e:
            last_error = e
            print(f"❌ Error with model {model_name}:")
            traceback.print_exc()

    raise last_error


def generate_reply(message: str) -> str:
    try:
        user_message = message.strip()

        if not user_message:
            return "Sila masukkan soalan berkaitan Bahasa Melayu SPM."

        if is_greeting(user_message):
            return (
                "Hai! Selamat datang. Saya tutor Bahasa Melayu SPM anda. "
                "Topik Bahasa Melayu SPM apa yang anda perlukan bantuan hari ini?"
            )

        return generate_with_fallback(user_message)

    except Exception as e:
        print("❌ Gemini Error:")
        traceback.print_exc()
        return "Maaf, AI assistant sedang menghadapi masalah. Sila cuba lagi."