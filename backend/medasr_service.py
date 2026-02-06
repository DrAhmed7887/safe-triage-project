import os
import re
from typing import Optional, List, Tuple
from pathlib import Path

USE_VERTEX_SPEECH = os.getenv("USE_VERTEX_SPEECH", "false").lower() in {"true", "1", "yes"}
DEFAULT_LANGUAGE_CODE = os.getenv("SPEECH_LANGUAGE", "ar-EG")
DEFAULT_SAMPLE_RATE = int(os.getenv("SPEECH_SAMPLE_RATE", "16000"))

# Optional: Google Cloud Speech-to-Text
speech = None
if USE_VERTEX_SPEECH:
    try:
        from google.cloud import speech_v1 as speech
    except Exception as e:
        print(f"[ASR] WARNING: google-cloud-speech not available: {e}")

# Optional: Google Gemini API (google-genai)
api_key = os.getenv("GEMINI_API_KEY")
genai = None
client = None
try:
    from google import genai as _genai
    genai = _genai
except Exception as e:
    print(f"[Gemini] WARNING: google-genai not available: {e}")

if api_key and genai:
    client = genai.Client(api_key=api_key)
    print("[Gemini] API configured")
elif not api_key:
    print("[Gemini] WARNING: No API key found")


class MedASRService:
    def __init__(self):
        self.provider = "disabled"
        self.available = False
        self._speech_client = None

        if speech and USE_VERTEX_SPEECH:
            try:
                self._speech_client = speech.SpeechClient()
                self.provider = "speech"
                self.available = True
                print("[ASR] Using Google Cloud Speech-to-Text")
            except Exception as e:
                print(f"[ASR] Failed to init Speech-to-Text: {e}")

        if not self.available and client is not None:
            self.provider = "gemini"
            self.available = True
            print("[ASR] Using Gemini multimodal")

        if not self.available:
            print("[ASR] Transcription service unavailable")

    def get_status(self) -> dict:
        return {"available": self.available, "provider": self.provider}

    def transcribe(
        self,
        audio_path: str,
        language_code: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> dict:
        if not self.available:
            return {"success": False, "error": "Voice transcription disabled"}

        if self.provider == "speech":
            requested_lang = (language_code or "").strip().lower()
            if requested_lang in {"auto", "auto-detect", "detect", "auto_detect"}:
                ar_result = self._transcribe_with_speech(
                    audio_path,
                    "ar-EG",
                    content_type,
                    alternative_languages=[],
                )
                en_result = self._transcribe_with_speech(
                    audio_path,
                    "en-US",
                    content_type,
                    alternative_languages=[],
                )

                if ar_result.get("success") and not en_result.get("success"):
                    return ar_result
                if en_result.get("success") and not ar_result.get("success"):
                    return en_result
                if not ar_result.get("success") and not en_result.get("success"):
                    return ar_result if ar_result.get("error") else en_result

                return self._select_best_transcription(ar_result, en_result)

            # Manual language selection: do NOT provide alternatives to avoid swaps
            return self._transcribe_with_speech(
                audio_path,
                language_code or DEFAULT_LANGUAGE_CODE,
                content_type,
                alternative_languages=[],
            )

        return self._transcribe_with_gemini(audio_path, content_type)

    def _detect_encoding(self, audio_path: str, content_type: Optional[str]):
        ct = (content_type or "").lower()
        ext = Path(audio_path).suffix.lower()

        if "webm" in ct or ext == ".webm":
            return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
        if "ogg" in ct or ext == ".ogg":
            return speech.RecognitionConfig.AudioEncoding.OGG_OPUS
        if "wav" in ct or ext == ".wav":
            return speech.RecognitionConfig.AudioEncoding.LINEAR16
        return speech.RecognitionConfig.AudioEncoding.LINEAR16

    def _transcribe_with_speech(
        self,
        audio_path: str,
        language_code: str,
        content_type: Optional[str] = None,
        alternative_languages: Optional[List[str]] = None,
    ) -> dict:
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            audio = speech.RecognitionAudio(content=audio_data)
            encoding = self._detect_encoding(audio_path, content_type)
            base_language = language_code or DEFAULT_LANGUAGE_CODE
            if alternative_languages is not None:
                alt_languages = alternative_languages
            else:
                if base_language.lower().startswith("ar"):
                    alt_languages = ["en-US"]
                elif base_language.lower().startswith("en"):
                    alt_languages = ["ar-EG"]
                else:
                    alt_languages = []

            config_kwargs = {
                "encoding": encoding,
                "language_code": base_language,
                "enable_automatic_punctuation": True,
            }
            if alt_languages:
                config_kwargs["alternative_language_codes"] = alt_languages
            if encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16:
                config_kwargs["sample_rate_hertz"] = DEFAULT_SAMPLE_RATE
            # Medical dictation model isn't available for ar-EG
            if base_language.lower().startswith("en-") and encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16:
                config_kwargs["model"] = "medical_dictation"
                config_kwargs["use_enhanced"] = True

            config = speech.RecognitionConfig(**config_kwargs)

            response = self._speech_client.recognize(config=config, audio=audio)
            transcript = " ".join([r.alternatives[0].transcript for r in response.results])
            confidence = self._extract_confidence(response)
            return {"success": True, "transcription": transcript.strip(), "confidence": confidence}
        except Exception as e:
            print(f"[ASR] Speech-to-Text error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _extract_confidence(response) -> float:
        confidences = []
        for result in getattr(response, "results", []) or []:
            if result.alternatives:
                conf = getattr(result.alternatives[0], "confidence", 0.0)
                if conf:
                    confidences.append(conf)
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    def _select_best_transcription(self, ar_result: dict, en_result: dict) -> dict:
        ar_text = ar_result.get("transcription", "")
        en_text = en_result.get("transcription", "")
        ar_conf = float(ar_result.get("confidence", 0.0) or 0.0)
        en_conf = float(en_result.get("confidence", 0.0) or 0.0)

        ar_score = ar_conf + self._arabic_ratio(ar_text)
        en_score = en_conf + self._latin_ratio(en_text)

        return ar_result if ar_score >= en_score else en_result

    @staticmethod
    def _arabic_ratio(text: str) -> float:
        if not text:
            return 0.0
        arabic_chars = re.findall(r"[\u0600-\u06FF]", text)
        return len(arabic_chars) / max(len(text), 1)

    @staticmethod
    def _latin_ratio(text: str) -> float:
        if not text:
            return 0.0
        latin_chars = re.findall(r"[A-Za-z]", text)
        return len(latin_chars) / max(len(text), 1)

    @staticmethod
    def _looks_english(text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        return re.fullmatch(r"[a-zA-Z\\s\\.,!?'-]+", cleaned) is not None

    def _transcribe_with_gemini(self, audio_path: str, content_type: Optional[str] = None) -> dict:
        if not client:
            return {"success": False, "error": "Gemini API not configured"}
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            mime_type = content_type or "audio/wav"

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_data,
                        }
                    },
                    "Transcribe this audio exactly. Detect whether it is Arabic or English and return the transcription in that same language. Return ONLY the transcription.",
                ],
            )

            transcription = response.text.strip()
            return {"success": True, "transcription": transcription}
        except Exception as e:
            print(f"[Gemini] ERROR: {str(e)}")
            return {"success": False, "error": str(e)}


medasr_service = MedASRService()
