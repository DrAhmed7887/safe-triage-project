from google import genai
import os

# Configure client at module load
api_key = os.getenv("GEMINI_API_KEY")
client = None

if api_key:
    client = genai.Client(api_key=api_key)
    print("[Gemini] API configured")
else:
    print("[Gemini] WARNING: No API key found")

class MedASRService:
    def __init__(self):
        self.available = client is not None
        print("[Gemini] Transcription service ready")
    
    def transcribe(self, audio_path: str) -> dict:
        if not client:
            return {"success": False, "error": "Gemini API not configured"}
            
        try:
            print(f"[Gemini] Transcribing: {audio_path}")
            
            # Upload file to Gemini using new SDK
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            # Generate transcription using new SDK
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": audio_data
                        }
                    },
                    "Transcribe this audio exactly. If Arabic, write Arabic. If English, write English. Return ONLY the transcription."
                ]
            )
            
            transcription = response.text.strip()
            print(f"[Gemini] Result: {transcription}")
            return {"success": True, "transcription": transcription}
            
        except Exception as e:
            print(f"[Gemini] ERROR: {str(e)}")
            return {"success": False, "error": str(e)}

medasr_service = MedASRService()
