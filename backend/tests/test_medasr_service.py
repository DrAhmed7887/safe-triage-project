"""
Unit tests for MedASRService (backend/medasr_service.py)
=========================================================

Coverage targets:
- Hallucination detection in _transcribe_with_gemini()
- Auto-mode language detection in transcribe()
- _select_best_transcription()
- _arabic_ratio() / _latin_ratio()
- _detect_encoding()
- _detect_sample_rate()
- _build_speech_contexts()
- _model_candidates()
- get_status()
- Edge cases: empty audio, unclear audio, API errors

Design note
-----------
The module-level `speech` variable is read at call time inside every method that
touches the Speech API (e.g. `_detect_encoding`, `_detect_sample_rate`).
We must therefore keep `backend.medasr_service.speech` patched for the entire
lifetime of each test, not just during service construction.

The `speech_ctx` fixture does exactly that: it patches the module-level name,
creates the service, and keeps the patch active for the whole test body.
"""

import contextlib
import tempfile
import types
import pytest
from unittest.mock import MagicMock, patch, call

import backend.medasr_service as _mod  # imported once so we can reference it easily


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_encoding_enum():
    """Minimal stand-in for speech.RecognitionConfig.AudioEncoding."""
    return types.SimpleNamespace(WEBM_OPUS=3, OGG_OPUS=6, LINEAR16=1, FLAC=2, MULAW=5)


def _make_speech_mock():
    """Build a minimal mock of google.cloud.speech_v1.

    Important: SpeechClient, RecognitionAudio, RecognitionConfig, and
    SpeechContext must all be MagicMock *instances* (i.e. MagicMock()), not
    the class itself.  Using the bare `MagicMock` class breaks `call_args`
    tracking because `call_args` is a property descriptor on the class, not
    a recorded-call attribute on the instance.
    """
    enc = _make_encoding_enum()
    RecognitionConfig = MagicMock()
    RecognitionConfig.AudioEncoding = enc
    return types.SimpleNamespace(
        SpeechClient=MagicMock(),
        RecognitionAudio=MagicMock(),
        RecognitionConfig=RecognitionConfig,
        SpeechContext=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def speech_ctx():
    """
    Fixture that patches `backend.medasr_service.speech` and
    `backend.medasr_service.USE_VERTEX_SPEECH` for the entire test,
    creates a MedASRService in speech mode, and yields (service, speech_mock).

    Usage:
        def test_something(speech_ctx):
            service, speech_mock = speech_ctx
    """
    speech_mock = _make_speech_mock()
    speech_mock.SpeechClient = MagicMock(return_value=MagicMock())

    with patch.object(_mod, "speech", speech_mock), \
         patch.object(_mod, "USE_VERTEX_SPEECH", True), \
         patch.object(_mod, "genai", None):  # disable Gemini so speech wins
        service = _mod.MedASRService()
        # Put the mock client on the service so recognize() calls are captured
        service._speech_client = MagicMock()
        yield service, speech_mock


@pytest.fixture
def gemini_ctx():
    """
    Fixture that patches genai + api_key so MedASRService uses the Gemini
    provider, and yields (service, genai_mock).
    """
    genai_mock = MagicMock()
    with patch.object(_mod, "genai", genai_mock), \
         patch.object(_mod, "api_key", "test-key"), \
         patch.object(_mod, "USE_VERTEX_SPEECH", False), \
         patch.object(_mod, "speech", None):
        service = _mod.MedASRService()
        # Keep genai active after construction too
        yield service, genai_mock


@pytest.fixture
def tmp_audio():
    """Return a helper that writes bytes to a temp file and returns its path."""
    created = []

    def _make(data: bytes, suffix: str = ".webm") -> str:
        f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        f.write(data)
        f.flush()
        f.close()
        created.append(f.name)
        return f.name

    yield _make


# ---------------------------------------------------------------------------
# 1. get_status()
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_disabled_when_no_providers(self):
        with patch.object(_mod, "genai", None), \
             patch.object(_mod, "api_key", None), \
             patch.object(_mod, "USE_VERTEX_SPEECH", False), \
             patch.object(_mod, "speech", None):
            service = _mod.MedASRService()

        status = service.get_status()
        assert status["available"] is False
        assert status["provider"] == "disabled"

    def test_gemini_provider_reported(self, gemini_ctx):
        service, _ = gemini_ctx
        status = service.get_status()
        assert status["available"] is True
        assert status["provider"] == "gemini"

    def test_speech_provider_reported(self, speech_ctx):
        service, _ = speech_ctx
        status = service.get_status()
        assert status["available"] is True
        assert status["provider"] == "speech"


# ---------------------------------------------------------------------------
# 2. transcribe() — disabled service
# ---------------------------------------------------------------------------

class TestTranscribeUnavailable:
    def test_returns_error_dict_when_disabled(self):
        with patch.object(_mod, "genai", None), \
             patch.object(_mod, "api_key", None), \
             patch.object(_mod, "USE_VERTEX_SPEECH", False), \
             patch.object(_mod, "speech", None):
            service = _mod.MedASRService()
            result = service.transcribe("/fake/audio.webm")

        assert result["success"] is False
        assert "disabled" in result["error"].lower()


# ---------------------------------------------------------------------------
# 3. Auto-mode language detection — single Speech API call
# ---------------------------------------------------------------------------

class TestAutoModeLanguageDetection:
    """
    When language is one of the 'auto' variants, the implementation MUST make
    exactly ONE _transcribe_with_speech call (ar-EG + en-US alternative),
    not two separate language-specific calls.
    """

    @pytest.mark.parametrize(
        "lang_code",
        ["auto", "Auto", "AUTO", "auto-detect", "detect", "auto_detect"],
    )
    def test_single_call_for_all_auto_variants(self, speech_ctx, lang_code):
        service, _ = speech_ctx
        with patch.object(service, "_transcribe_with_speech") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe("/fake/audio.webm", language_code=lang_code)

        assert mock_fn.call_count == 1, (
            f"Expected 1 call for lang='{lang_code}', got {mock_fn.call_count}"
        )

    def test_ar_eg_is_primary_language_in_auto_mode(self, speech_ctx):
        service, _ = speech_ctx
        with patch.object(service, "_transcribe_with_speech") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe("/fake/audio.webm", language_code="auto")

        positional = mock_fn.call_args[0]
        assert positional[1] == "ar-EG", f"Primary language should be ar-EG, got {positional[1]}"

    def test_en_us_is_alternative_in_auto_mode(self, speech_ctx):
        service, _ = speech_ctx
        with patch.object(service, "_transcribe_with_speech") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe("/fake/audio.webm", language_code="auto")

        _, kwargs = mock_fn.call_args
        assert "en-US" in kwargs.get("alternative_languages", [])

    def test_manual_language_passes_empty_alternatives(self, speech_ctx):
        service, _ = speech_ctx
        with patch.object(service, "_transcribe_with_speech") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe("/fake/audio.webm", language_code="ar-EG")

        _, kwargs = mock_fn.call_args
        assert kwargs.get("alternative_languages") == []


# ---------------------------------------------------------------------------
# 4. _arabic_ratio()
# ---------------------------------------------------------------------------

class TestArabicRatio:
    def test_pure_arabic_text_high_ratio(self):
        ratio = _mod.MedASRService._arabic_ratio("صدري بيوجعني")
        assert ratio > 0.5

    def test_pure_english_text_is_zero(self):
        assert _mod.MedASRService._arabic_ratio("chest pain") == 0.0

    def test_empty_string_is_zero(self):
        assert _mod.MedASRService._arabic_ratio("") == 0.0

    def test_mixed_text_partial_ratio(self):
        # "abc صدر" — roughly equal Arabic and Latin chars
        ratio = _mod.MedASRService._arabic_ratio("abc \u0635\u062f\u0631")
        assert 0.0 < ratio < 1.0

    def test_punctuation_only_is_zero(self):
        assert _mod.MedASRService._arabic_ratio("... , ! ?") == 0.0

    def test_unicode_arabic_range_counted(self):
        # U+0600 (Arabic) to U+06FF boundary chars
        ratio = _mod.MedASRService._arabic_ratio("\u0600\u06FF")
        assert ratio == 1.0


# ---------------------------------------------------------------------------
# 5. _latin_ratio()
# ---------------------------------------------------------------------------

class TestLatinRatio:
    def test_pure_english_text_high_ratio(self):
        ratio = _mod.MedASRService._latin_ratio("chest pain headache")
        assert ratio > 0.7

    def test_pure_arabic_text_is_zero(self):
        assert _mod.MedASRService._latin_ratio("صدري بيوجعني") == 0.0

    def test_empty_string_is_zero(self):
        assert _mod.MedASRService._latin_ratio("") == 0.0

    def test_digits_not_counted_as_latin(self):
        assert _mod.MedASRService._latin_ratio("12345") == 0.0

    def test_mixed_text_partial_ratio(self):
        ratio = _mod.MedASRService._latin_ratio("abc \u0635\u062f\u0631")
        assert 0.0 < ratio < 1.0

    def test_uppercase_and_lowercase_both_counted(self):
        ratio_upper = _mod.MedASRService._latin_ratio("ABC")
        ratio_lower = _mod.MedASRService._latin_ratio("abc")
        assert ratio_upper == ratio_lower == 1.0


# ---------------------------------------------------------------------------
# 6. _detect_encoding()
# ---------------------------------------------------------------------------

class TestDetectEncoding:
    def test_webm_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.webm", "audio/webm")
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS

    def test_webm_extension_no_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.webm", None)
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS

    def test_ogg_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.ogg", "audio/ogg")
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.OGG_OPUS

    def test_ogg_extension_no_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.ogg", None)
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.OGG_OPUS

    def test_wav_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.wav", "audio/wav")
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.LINEAR16

    def test_wav_extension_no_content_type(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.wav", None)
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.LINEAR16

    def test_unknown_format_defaults_to_linear16(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.mp3", "audio/mpeg")
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.LINEAR16

    def test_content_type_webm_overrides_wav_extension(self, speech_ctx):
        """If content-type says webm, it wins even with a .wav extension."""
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/file.wav", "audio/webm")
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS

    def test_no_content_type_no_extension_defaults_linear16(self, speech_ctx):
        service, speech_mock = speech_ctx
        enc = service._detect_encoding("/audio/unknown", None)
        assert enc == speech_mock.RecognitionConfig.AudioEncoding.LINEAR16


# ---------------------------------------------------------------------------
# 7. _detect_sample_rate()
# ---------------------------------------------------------------------------

class TestDetectSampleRate:
    def test_webm_opus_returns_opus_sample_rate(self, speech_ctx):
        service, speech_mock = speech_ctx
        rate = service._detect_sample_rate(speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert rate == _mod.DEFAULT_OPUS_SAMPLE_RATE

    def test_ogg_opus_returns_opus_sample_rate(self, speech_ctx):
        service, speech_mock = speech_ctx
        rate = service._detect_sample_rate(speech_mock.RecognitionConfig.AudioEncoding.OGG_OPUS)
        assert rate == _mod.DEFAULT_OPUS_SAMPLE_RATE

    def test_linear16_returns_default_sample_rate(self, speech_ctx):
        service, speech_mock = speech_ctx
        rate = service._detect_sample_rate(speech_mock.RecognitionConfig.AudioEncoding.LINEAR16)
        assert rate == _mod.DEFAULT_SAMPLE_RATE

    def test_unrecognised_encoding_returns_none(self, speech_ctx):
        service, _ = speech_ctx
        rate = service._detect_sample_rate(9999)
        assert rate is None

    def test_opus_rate_is_48000_by_default(self, speech_ctx):
        service, speech_mock = speech_ctx
        rate = service._detect_sample_rate(speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert rate == 48000


# ---------------------------------------------------------------------------
# 8. _build_speech_contexts()
# ---------------------------------------------------------------------------

class TestBuildSpeechContexts:
    def _get_phrases(self, speech_ctx, lang):
        service, speech_mock = speech_ctx
        service._build_speech_contexts(lang)
        return speech_mock.SpeechContext.call_args[1]["phrases"]

    def test_arabic_language_includes_arabic_phrases(self, speech_ctx):
        phrases = self._get_phrases(speech_ctx, "ar-EG")
        has_arabic = any(
            "\u0600" <= ch <= "\u06FF"
            for phrase in phrases
            for ch in phrase
        )
        assert has_arabic

    def test_english_language_includes_chest_pain(self, speech_ctx):
        phrases = self._get_phrases(speech_ctx, "en-US")
        assert "chest pain" in phrases

    def test_unknown_language_includes_both_sets(self, speech_ctx):
        phrases = self._get_phrases(speech_ctx, "zh-CN")
        has_arabic = any(
            "\u0600" <= ch <= "\u06FF"
            for phrase in phrases
            for ch in phrase
        )
        assert has_arabic and "chest pain" in phrases

    def test_returns_list_of_length_one(self, speech_ctx):
        service, _ = speech_ctx
        contexts = service._build_speech_contexts("ar-EG")
        assert isinstance(contexts, list)
        assert len(contexts) == 1

    def test_boost_value_is_10(self, speech_ctx):
        service, speech_mock = speech_ctx
        service._build_speech_contexts("ar-EG")
        assert speech_mock.SpeechContext.call_args[1]["boost"] == 10.0

    def test_arabic_language_includes_english_fallback_phrases(self, speech_ctx):
        """Arabic lang should also include English hints for bilingual patients."""
        phrases = self._get_phrases(speech_ctx, "ar-EG")
        assert "chest pain" in phrases


# ---------------------------------------------------------------------------
# 9. _model_candidates()
# ---------------------------------------------------------------------------

class TestModelCandidates:
    def test_default_model_in_candidates(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert _mod.DEFAULT_SPEECH_MODEL in candidates

    def test_fallback_model_in_candidates(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert _mod.FALLBACK_SPEECH_MODEL in candidates

    def test_no_duplicate_models(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert len(candidates) == len(set(candidates))

    def test_unsupported_model_excluded(self, speech_ctx):
        service, speech_mock = speech_ctx
        service._unsupported_models.add("chirp_2")
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert "chirp_2" not in candidates

    def test_medical_dictation_added_for_english_linear16(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("en-US", speech_mock.RecognitionConfig.AudioEncoding.LINEAR16)
        assert "medical_dictation" in candidates

    def test_medical_dictation_not_added_for_arabic(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.LINEAR16)
        assert "medical_dictation" not in candidates

    def test_medical_dictation_not_added_for_english_opus(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("en-US", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert "medical_dictation" not in candidates

    def test_medical_dictation_excluded_if_already_unsupported(self, speech_ctx):
        service, speech_mock = speech_ctx
        service._unsupported_models.add("medical_dictation")
        candidates = service._model_candidates("en-US", speech_mock.RecognitionConfig.AudioEncoding.LINEAR16)
        assert "medical_dictation" not in candidates

    def test_returns_non_empty_list(self, speech_ctx):
        service, speech_mock = speech_ctx
        candidates = service._model_candidates("ar-EG", speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS)
        assert len(candidates) > 0


# ---------------------------------------------------------------------------
# 10. _select_best_transcription()
# ---------------------------------------------------------------------------

class TestSelectBestTranscription:
    @staticmethod
    def _result(text, confidence):
        return {"success": True, "transcription": text, "confidence": confidence}

    def test_higher_confidence_arabic_wins(self, gemini_ctx):
        service, _ = gemini_ctx
        ar = self._result("صدري بيوجعني", 0.9)
        en = self._result("chest pain", 0.3)
        assert service._select_best_transcription(ar, en) is ar

    def test_arabic_text_ratio_breaks_tie(self, gemini_ctx):
        service, _ = gemini_ctx
        ar = self._result("صدري بيوجعني", 0.5)
        en = self._result("chest pain", 0.5)
        # ar_score = 0.5 + arabic_ratio(...) >> 0.5 + 0
        assert service._select_best_transcription(ar, en) is ar

    def test_high_confidence_english_wins_over_low_confidence_arabic(self, gemini_ctx):
        service, _ = gemini_ctx
        ar = self._result("صدر", 0.1)
        en = self._result("chest pain", 0.95)
        assert service._select_best_transcription(ar, en) is en

    def test_empty_arabic_loses_to_scored_english(self, gemini_ctx):
        service, _ = gemini_ctx
        ar = self._result("", 0.0)
        en = self._result("shortness of breath", 0.8)
        assert service._select_best_transcription(ar, en) is en

    def test_both_empty_returns_arabic_result(self, gemini_ctx):
        """Tie at 0 — ar_score >= en_score, so Arabic result is returned."""
        service, _ = gemini_ctx
        ar = self._result("", 0.0)
        en = self._result("", 0.0)
        assert service._select_best_transcription(ar, en) is ar

    def test_none_confidence_treated_as_zero(self, gemini_ctx):
        service, _ = gemini_ctx
        ar = {"success": True, "transcription": "صدر", "confidence": None}
        en = {"success": True, "transcription": "chest", "confidence": 0.8}
        assert service._select_best_transcription(ar, en) is en


# ---------------------------------------------------------------------------
# 11. Hallucination detection in _transcribe_with_gemini()
# ---------------------------------------------------------------------------

class TestHallucinationDetection:
    """
    Heuristic: audio_seconds = len(audio_data) / 8000
    Condition:  audio_seconds < 2 AND len(transcription) > 200  →  reject
    Threshold in bytes: < 16 000 bytes = < 2 s.
    """

    @staticmethod
    def _gemini_response(text):
        r = MagicMock()
        r.text = text
        return r

    def test_short_audio_long_transcription_rejected(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 8000)  # 8000 B = 1 s
        long_text = "ع" * 201  # > 200 chars

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(long_text)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False
        # Error message must reference unreliability
        assert "unreliable" in result["error"].lower() or "موثوق" in result["error"]

    def test_short_audio_short_transcription_passes(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 8000)
        short_text = "صدري بيوجعني"  # < 200 chars

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(short_text)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is True
        assert result["transcription"] == short_text

    def test_long_audio_long_transcription_passes(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)  # 32 000 B = 4 s
        long_text = "ع" * 201

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(long_text)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is True

    def test_exactly_16000_bytes_passes_boundary(self, gemini_ctx, tmp_audio):
        """16 000 B / 8000 = 2.0 s; condition is < 2, so 2.0 is NOT rejected."""
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 16000)
        long_text = "ع" * 201

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(long_text)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is True

    def test_exactly_200_chars_with_short_audio_passes(self, gemini_ctx, tmp_audio):
        """200 chars is NOT > 200, so it should pass even with short audio."""
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 8000)
        text_200 = "a" * 200

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(text_200)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is True

    def test_201_chars_with_short_audio_rejected(self, gemini_ctx, tmp_audio):
        """201 chars > 200 with short audio IS hallucination-flagged."""
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 8000)
        text_201 = "a" * 201

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(text_201)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False

    def test_just_under_16000_bytes_long_transcription_rejected(self, gemini_ctx, tmp_audio):
        """15 999 B / 8000 = 1.999…s < 2 — should still be rejected."""
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 15999)
        long_text = "a" * 201

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response(long_text)

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# 12. Unclear audio from Gemini
# ---------------------------------------------------------------------------

class TestUnclearAudio:
    @staticmethod
    def _gemini_response(text):
        r = MagicMock()
        r.text = text
        return r

    def test_unclear_audio_marker_returns_error(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response("[unclear audio]")

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False
        assert "unclear" in result["error"].lower() or "واضح" in result["error"]

    def test_unclear_marker_is_case_insensitive(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response("[UNCLEAR AUDIO]")

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False

    def test_empty_transcription_returns_error(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response("")

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False

    def test_whitespace_only_transcription_returns_error(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.return_value = self._gemini_response("   ")

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# 13. Gemini API error handling
# ---------------------------------------------------------------------------

class TestGeminiAPIErrors:
    def test_api_exception_message_in_error(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        model_mock.generate_content.side_effect = Exception("API quota exceeded")

        result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False
        assert "API quota exceeded" in result["error"]

    def test_genai_none_returns_not_configured_error(self, tmp_audio):
        audio_path = tmp_audio(b"x" * 32000)

        # Build a service with provider=gemini but genai is None at call time
        with patch.object(_mod, "genai", MagicMock()), \
             patch.object(_mod, "api_key", "key"), \
             patch.object(_mod, "USE_VERTEX_SPEECH", False), \
             patch.object(_mod, "speech", None):
            service = _mod.MedASRService()

        # Now patch genai to None so the method body sees None
        with patch.object(_mod, "genai", None):
            result = service._transcribe_with_gemini(audio_path, "audio/webm")

        assert result["success"] is False
        assert "not configured" in result["error"].lower()

    def test_file_not_found_returns_error(self, gemini_ctx):
        service, genai_mock = gemini_ctx
        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock

        result = service._transcribe_with_gemini("/nonexistent/audio.webm", "audio/webm")

        assert result["success"] is False

    def test_default_mime_type_when_none(self, gemini_ctx, tmp_audio):
        """content_type=None should default to audio/webm and not crash."""
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        model_mock = MagicMock()
        genai_mock.GenerativeModel.return_value = model_mock
        r = MagicMock()
        r.text = "chest pain"
        model_mock.generate_content.return_value = r

        result = service._transcribe_with_gemini(audio_path, None)

        assert result["success"] is True


# ---------------------------------------------------------------------------
# 14. _transcribe_with_speech() — full integration with mock client
# ---------------------------------------------------------------------------

def _speech_response(text, confidence=0.9):
    """Build a mock Speech API response."""
    alt = MagicMock()
    alt.transcript = text
    alt.confidence = confidence
    result_item = MagicMock()
    result_item.alternatives = [alt]
    resp = MagicMock()
    resp.results = [result_item]
    return resp


class TestTranscribeWithSpeech:
    def test_successful_transcription(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("chest pain", 0.85)

        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        assert result["success"] is True
        assert result["transcription"] == "chest pain"
        assert result["confidence"] == pytest.approx(0.85)

    def test_result_includes_model_and_encoding_fields(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("fever")

        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        assert "model" in result
        assert "encoding" in result
        assert result["encoding"] == "WEBM_OPUS"

    def test_unsupported_model_error_adds_to_skip_set(self, speech_ctx, tmp_audio):
        service, _ = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.side_effect = Exception(
            "incorrect model specified for this request"
        )

        service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        assert len(service._unsupported_models) > 0

    def test_generic_api_error_propagated(self, speech_ctx, tmp_audio):
        service, _ = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.side_effect = Exception("network failure")

        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        assert result["success"] is False
        assert "network failure" in result["error"]

    def test_empty_transcript_falls_through_to_next_model(self, speech_ctx, tmp_audio):
        """When the first model returns empty results, the next model should be tried."""
        service, _ = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")

        empty_resp = MagicMock()
        empty_resp.results = []
        good_resp = _speech_response("abdominal pain", 0.7)

        # First call: empty; subsequent calls: good result
        service._speech_client.recognize.side_effect = [
            empty_resp, good_resp, good_resp, good_resp
        ]

        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        assert result["success"] is True
        assert result["transcription"] == "abdominal pain"
        assert service._speech_client.recognize.call_count >= 2

    def test_file_not_found_returns_error(self, speech_ctx):
        service, _ = speech_ctx
        result = service._transcribe_with_speech("/no/such/file.webm", "ar-EG")
        assert result["success"] is False

    def test_alternative_languages_passed_in_config(self, speech_ctx, tmp_audio):
        """When alt_languages is non-empty, the config includes it."""
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", ["en-US"])

        config_call_kwargs = speech_mock.RecognitionConfig.call_args[1]
        assert "alternative_language_codes" in config_call_kwargs
        assert "en-US" in config_call_kwargs["alternative_language_codes"]

    def test_no_alternative_languages_when_empty_list(self, speech_ctx, tmp_audio):
        """Empty alt list means the config key should NOT be present."""
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        config_call_kwargs = speech_mock.RecognitionConfig.call_args[1]
        assert "alternative_language_codes" not in config_call_kwargs


# ---------------------------------------------------------------------------
# 15. _extract_confidence()
# ---------------------------------------------------------------------------

class TestExtractConfidence:
    def test_single_result_confidence(self):
        alt = MagicMock()
        alt.confidence = 0.75
        r = MagicMock()
        r.alternatives = [alt]
        resp = MagicMock()
        resp.results = [r]
        assert _mod.MedASRService._extract_confidence(resp) == pytest.approx(0.75)

    def test_averages_multiple_results(self):
        def _r(c):
            alt = MagicMock()
            alt.confidence = c
            r = MagicMock()
            r.alternatives = [alt]
            return r

        resp = MagicMock()
        resp.results = [_r(0.8), _r(0.6)]
        assert _mod.MedASRService._extract_confidence(resp) == pytest.approx(0.7)

    def test_zero_when_empty_results(self):
        resp = MagicMock()
        resp.results = []
        assert _mod.MedASRService._extract_confidence(resp) == 0.0

    def test_zero_confidence_value_excluded_from_average(self):
        """Confidences of 0.0 are falsy and excluded from the average."""
        alt = MagicMock()
        alt.confidence = 0.0
        r = MagicMock()
        r.alternatives = [alt]
        resp = MagicMock()
        resp.results = [r]
        assert _mod.MedASRService._extract_confidence(resp) == 0.0

    def test_missing_results_attr_returns_zero(self):
        resp = MagicMock(spec=[])  # spec=[] means no attributes
        assert _mod.MedASRService._extract_confidence(resp) == 0.0


# ---------------------------------------------------------------------------
# 16. transcribe() routing
# ---------------------------------------------------------------------------

class TestTranscribeRouting:
    def test_gemini_provider_routes_to_transcribe_with_gemini(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        with patch.object(service, "_transcribe_with_gemini") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe(audio_path)

        assert mock_fn.call_count == 1

    def test_speech_provider_routes_to_transcribe_with_speech(self, speech_ctx, tmp_audio):
        service, _ = speech_ctx
        audio_path = tmp_audio(b"x" * 32000)

        with patch.object(service, "_transcribe_with_speech") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe(audio_path, language_code="ar-EG")

        assert mock_fn.call_count == 1

    def test_content_type_forwarded_to_gemini(self, gemini_ctx, tmp_audio):
        service, genai_mock = gemini_ctx
        audio_path = tmp_audio(b"x" * 32000)

        with patch.object(service, "_transcribe_with_gemini") as mock_fn:
            mock_fn.return_value = {"success": True, "transcription": "test"}
            service.transcribe(audio_path, content_type="audio/ogg")

        args = mock_fn.call_args[0]
        assert args[1] == "audio/ogg"


# ---------------------------------------------------------------------------
# 17. Additional coverage: uncovered branches
# ---------------------------------------------------------------------------

class TestEncodingName:
    """_encoding_name() is a static method; covers lines 171-175."""

    def test_webm_opus_name(self, speech_ctx):
        service, speech_mock = speech_ctx
        name = _mod.MedASRService._encoding_name(
            speech_mock.RecognitionConfig.AudioEncoding.WEBM_OPUS
        )
        assert name == "WEBM_OPUS"

    def test_ogg_opus_name(self, speech_ctx):
        service, speech_mock = speech_ctx
        name = _mod.MedASRService._encoding_name(
            speech_mock.RecognitionConfig.AudioEncoding.OGG_OPUS
        )
        assert name == "OGG_OPUS"

    def test_linear16_name(self, speech_ctx):
        service, speech_mock = speech_ctx
        name = _mod.MedASRService._encoding_name(
            speech_mock.RecognitionConfig.AudioEncoding.LINEAR16
        )
        assert name == "LINEAR16"

    def test_unknown_encoding_returns_unknown(self, speech_ctx):
        name = _mod.MedASRService._encoding_name(9999)
        assert name == "UNKNOWN"


class TestSpeechClientInitFailure:
    """Covers lines 109-110: SpeechClient() raises in __init__, falls back to Gemini."""

    def test_falls_back_to_gemini_when_speech_client_init_fails(self):
        bad_speech = _make_speech_mock()
        bad_speech.SpeechClient = MagicMock(side_effect=Exception("auth failure"))
        genai_mock = MagicMock()

        with patch.object(_mod, "speech", bad_speech), \
             patch.object(_mod, "USE_VERTEX_SPEECH", True), \
             patch.object(_mod, "genai", genai_mock), \
             patch.object(_mod, "api_key", "test-key"):
            service = _mod.MedASRService()

        assert service.provider == "gemini"
        assert service.available is True


class TestAlternativeLanguagesFallback:
    """
    Covers lines 234-239: the branch where alternative_languages is None
    (not passed), so the method infers defaults based on the base_language.
    """

    def test_arabic_base_infers_english_alternative(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        # Pass alternative_languages=None to trigger the inference branch
        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", None)

        config_kwargs = speech_mock.RecognitionConfig.call_args[1]
        assert "alternative_language_codes" in config_kwargs
        assert "en-US" in config_kwargs["alternative_language_codes"]

    def test_english_base_infers_arabic_alternative(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        result = service._transcribe_with_speech(audio_path, "en-US", "audio/webm", None)

        config_kwargs = speech_mock.RecognitionConfig.call_args[1]
        assert "alternative_language_codes" in config_kwargs
        assert "ar-EG" in config_kwargs["alternative_language_codes"]

    def test_unknown_base_infers_empty_alternatives(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        result = service._transcribe_with_speech(audio_path, "zh-CN", "audio/webm", None)

        config_kwargs = speech_mock.RecognitionConfig.call_args[1]
        # Empty alt list → key should not appear
        assert "alternative_language_codes" not in config_kwargs


class TestMedicalDictationEnhanced:
    """Covers line 261: use_enhanced=True is added for the medical_dictation model."""

    def test_use_enhanced_set_for_medical_dictation(self, speech_ctx, tmp_audio):
        service, speech_mock = speech_ctx
        audio_path = tmp_audio(b"x" * 32000, suffix=".wav")

        # Force medical_dictation to be the first (and only) candidate
        service._unsupported_models.clear()
        with patch.object(service, "_model_candidates", return_value=["medical_dictation"]):
            service._speech_client.recognize.return_value = _speech_response("headache")
            service._transcribe_with_speech(audio_path, "en-US", "audio/wav", [])

        config_kwargs = speech_mock.RecognitionConfig.call_args[1]
        assert config_kwargs.get("use_enhanced") is True


class TestShortAudioWarning:
    """Covers line 224: the MIN_AUDIO_BYTES short-payload log warning path."""

    def test_short_payload_still_attempts_transcription(self, speech_ctx, tmp_audio):
        """Even with a very short payload the method tries transcription (just logs a warning)."""
        service, speech_mock = speech_ctx
        # Write fewer bytes than MIN_AUDIO_BYTES (default 800)
        audio_path = tmp_audio(b"x" * 10, suffix=".webm")
        service._speech_client.recognize.return_value = _speech_response("test")

        result = service._transcribe_with_speech(audio_path, "ar-EG", "audio/webm", [])

        # Should succeed — warning is just a log, not a hard failure
        assert result["success"] is True
