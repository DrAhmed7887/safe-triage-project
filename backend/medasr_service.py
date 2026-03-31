import base64
import os
import re
from typing import Optional, List, Tuple
from pathlib import Path

USE_VERTEX_SPEECH = os.getenv("USE_VERTEX_SPEECH", "false").lower() in {"true", "1", "yes"}
DEFAULT_LANGUAGE_CODE = os.getenv("SPEECH_LANGUAGE", "ar-EG")
DEFAULT_SAMPLE_RATE = int(os.getenv("SPEECH_SAMPLE_RATE", "16000"))
DEFAULT_OPUS_SAMPLE_RATE = int(os.getenv("SPEECH_OPUS_SAMPLE_RATE", "48000"))
DEFAULT_SPEECH_MODEL = os.getenv("SPEECH_MODEL", "chirp_2").strip() or "chirp_2"
FALLBACK_SPEECH_MODEL = os.getenv("SPEECH_FALLBACK_MODEL", "latest_long").strip() or "latest_long"
MIN_AUDIO_BYTES = int(os.getenv("SPEECH_MIN_AUDIO_BYTES", "800"))

MEDICAL_HINTS_AR = [
    "صدري بيوجعني",
    "مش قادر اتنفس",
    "بطني بتوجعني",
    "عندي سخونية",
    "دوخة",
    "غثيان",
    "ترجيع",
    "صداع",
    "دم في البراز",
    "انتحار",
]

MEDICAL_HINTS_EN = [
    "chest pain",
    "shortness of breath",
    "abdominal pain",
    "fever",
    "dizziness",
    "nausea",
    "vomiting",
    "headache",
    "blood in stool",
    "suicidal ideation",
]

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
        self._unsupported_models = set()

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
                    alternative_languages=["en-US"],
                )
                en_result = self._transcribe_with_speech(
                    audio_path,
                    "en-US",
                    content_type,
                    alternative_languages=["ar-EG"],
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

    @staticmethod
    def _encoding_name(encoding) -> str:
        if encoding == speech.RecognitionConfig.AudioEncoding.WEBM_OPUS:
            return "WEBM_OPUS"
        if encoding == speech.RecognitionConfig.AudioEncoding.OGG_OPUS:
            return "OGG_OPUS"
        if encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16:
            return "LINEAR16"
        return "UNKNOWN"

    def _detect_sample_rate(self, encoding: int) -> Optional[int]:
        if encoding in {
            speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        }:
            return DEFAULT_OPUS_SAMPLE_RATE
        if encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16:
            return DEFAULT_SAMPLE_RATE
        return None

    def _build_speech_contexts(self, language_code: str):
        lang = (language_code or "").lower()
        if lang.startswith("ar"):
            phrases = MEDICAL_HINTS_AR + MEDICAL_HINTS_EN
        elif lang.startswith("en"):
            phrases = MEDICAL_HINTS_EN + MEDICAL_HINTS_AR
        else:
            phrases = MEDICAL_HINTS_AR + MEDICAL_HINTS_EN
        return [speech.SpeechContext(phrases=phrases, boost=10.0)]

    def _model_candidates(self, language_code: str, encoding: int) -> List[str]:
        candidates: List[str] = []
        for model_name in [DEFAULT_SPEECH_MODEL, FALLBACK_SPEECH_MODEL, "latest_long", "default"]:
            cleaned = (model_name or "").strip()
            if cleaned and cleaned not in candidates and cleaned not in self._unsupported_models:
                candidates.append(cleaned)
        if (
            (language_code or "").lower().startswith("en-")
            and encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
            and "medical_dictation" not in candidates
            and "medical_dictation" not in self._unsupported_models
        ):
            candidates.append("medical_dictation")
        return candidates

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

            if len(audio_data) < MIN_AUDIO_BYTES:
                print(f"[ASR] WARNING: very short audio payload ({len(audio_data)} bytes)", flush=True)

            audio = speech.RecognitionAudio(content=audio_data)
            encoding = self._detect_encoding(audio_path, content_type)
            encoding_name = self._encoding_name(encoding)
            sample_rate = self._detect_sample_rate(encoding)
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

            print(
                f"[ASR] STT request bytes={len(audio_data)} encoding={encoding_name} "
                f"sample_rate={sample_rate} language={base_language} alt={alt_languages}",
                flush=True,
            )

            errors: List[str] = []
            for model_name in self._model_candidates(base_language, encoding):
                config_kwargs = {
                    "encoding": encoding,
                    "language_code": base_language,
                    "enable_automatic_punctuation": True,
                    "model": model_name,
                    "speech_contexts": self._build_speech_contexts(base_language),
                }
                if alt_languages:
                    config_kwargs["alternative_language_codes"] = alt_languages
                if sample_rate:
                    config_kwargs["sample_rate_hertz"] = sample_rate
                if model_name == "medical_dictation":
                    config_kwargs["use_enhanced"] = True

                try:
                    config = speech.RecognitionConfig(**config_kwargs)
                    response = self._speech_client.recognize(config=config, audio=audio)
                    transcript = " ".join([r.alternatives[0].transcript for r in response.results]).strip()
                    confidence = self._extract_confidence(response)
                    print(
                        f"[ASR] Model={model_name} transcript_len={len(transcript)} confidence={confidence:.2f}",
                        flush=True,
                    )
                    if transcript:
                        return {
                            "success": True,
                            "transcription": transcript,
                            "confidence": confidence,
                            "model": model_name,
                            "encoding": encoding_name,
                        }
                    errors.append(f"{model_name}: empty transcript")
                except Exception as model_exc:
                    model_error = str(model_exc)
                    if "incorrect model specified" in model_error.lower():
                        self._unsupported_models.add(model_name)
                    errors.append(f"{model_name}: {model_error}")
                    print(f"[ASR] Model {model_name} failed: {model_error}", flush=True)

            return {"success": False, "error": " | ".join(errors) if errors else "Speech recognition returned empty transcript"}
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

            mime_type = content_type or "audio/webm"
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": audio_b64,
                                }
                            },
                            {
                                "text": "Transcribe this audio exactly. Detect whether it is Arabic or English and return the transcription in that same language. Return ONLY the transcription."
                            },
                        ]
                    }
                ],
            )

            transcription = response.text.strip()
            return {"success": True, "transcription": transcription}
        except Exception as e:
            print(f"[Gemini] ERROR: {str(e)}")
            return {"success": False, "error": str(e)}


medasr_service = MedASRService()
