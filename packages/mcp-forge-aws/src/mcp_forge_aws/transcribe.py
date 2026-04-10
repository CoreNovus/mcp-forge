"""Amazon Transcribe provider for mcp-forge.

Accepts raw audio bytes (not S3 URIs) — handles upload internally.
Supports auto language detection and speaker diarization.

Example::

    transcriber = AWSTranscribeProvider(region="us-east-1")
    result = await transcriber.transcribe(audio_bytes, language="en")
    print(result.text)
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import aioboto3

from mcp_forge_core.providers.transcribe import BaseTranscribeProvider, TranscriptionResult

logger = logging.getLogger(__name__)

_LANGUAGE_MAP = {
    "en": "en-US", "zh": "zh-TW", "ja": "ja-JP", "ko": "ko-KR",
    "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-BR",
    "it": "it-IT", "nl": "nl-NL", "ru": "ru-RU", "ar": "ar-SA",
}


class AWSTranscribeProvider(BaseTranscribeProvider):
    """Amazon Transcribe provider.

    Accepts raw audio bytes, uploads to a temporary S3 location,
    runs the transcription job, and returns structured results.

    Args:
        region: AWS region.
        output_bucket: S3 bucket for Transcribe output.
        media_format: Audio format (default: "wav").
        poll_interval: Seconds between status polls (default: 5).
        max_poll_attempts: Max polls before timeout (default: 360 = 30min).
        session: Optional shared aioboto3.Session.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        output_bucket: str | None = None,
        media_format: str = "wav",
        poll_interval: int = 5,
        max_poll_attempts: int = 360,
        session: aioboto3.Session | None = None,
    ) -> None:
        self._region = region
        self._output_bucket = output_bucket or f"mcp-forge-transcribe-{region}"
        self._media_format = media_format
        self._poll_interval = poll_interval
        self._max_poll_attempts = max_poll_attempts
        self._session = session or aioboto3.Session()

    async def transcribe(
        self,
        audio_data: bytes,
        *,
        language: str | None = None,
        enable_diarization: bool = False,
    ) -> TranscriptionResult:
        """Transcribe audio data to text.

        Uploads audio to S3, starts a Transcribe job, polls for completion,
        and returns structured results.
        """
        job_name = f"mcp-forge-{uuid.uuid4().hex[:12]}"
        s3_key = f"transcribe-input/{job_name}.{self._media_format}"
        s3_uri = f"s3://{self._output_bucket}/{s3_key}"

        # Upload audio to S3
        async with self._session.client(
            "s3", region_name=self._region
        ) as s3:
            await s3.put_object(
                Bucket=self._output_bucket,
                Key=s3_key,
                Body=audio_data,
            )

        # Start transcription job
        job_params: dict[str, Any] = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": s3_uri},
            "MediaFormat": self._media_format,
            "OutputBucketName": self._output_bucket,
        }

        lang_code = _LANGUAGE_MAP.get(language, language) if language else None
        if lang_code:
            job_params["LanguageCode"] = lang_code
        else:
            job_params["IdentifyLanguage"] = True

        if enable_diarization:
            job_params["Settings"] = {
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 10,
            }

        async with self._session.client(
            "transcribe", region_name=self._region
        ) as transcribe:
            await transcribe.start_transcription_job(**job_params)

            # Poll for completion
            for _ in range(self._max_poll_attempts):
                response = await transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response["TranscriptionJob"]["TranscriptionJobStatus"]

                if status == "COMPLETED":
                    break
                if status == "FAILED":
                    reason = response["TranscriptionJob"].get("FailureReason", "Unknown")
                    raise RuntimeError(f"Transcription failed: {reason}")

                import asyncio
                await asyncio.sleep(self._poll_interval)
            else:
                raise TimeoutError(f"Transcription job {job_name} timed out")

        # Fetch results from S3
        result_key = f"{job_name}.json"
        async with self._session.client(
            "s3", region_name=self._region
        ) as s3:
            obj = await s3.get_object(
                Bucket=self._output_bucket,
                Key=result_key,
            )
            result_body = json.loads(await obj["Body"].read())

        return self._parse_result(result_body, lang_code)

    @staticmethod
    def _parse_result(
        result: dict[str, Any],
        expected_language: str | None,
    ) -> TranscriptionResult:
        """Parse AWS Transcribe JSON result into TranscriptionResult."""
        results = result.get("results", {})
        transcripts = results.get("transcripts", [])
        full_text = " ".join(t.get("transcript", "") for t in transcripts)

        items = results.get("items", [])
        segments: list[dict] = []
        for i, item in enumerate(items):
            if item.get("type") == "pronunciation":
                segments.append({
                    "id": i,
                    "start": float(item.get("start_time", 0)),
                    "end": float(item.get("end_time", 0)),
                    "text": item.get("alternatives", [{}])[0].get("content", ""),
                })

        detected_lang = expected_language or results.get("language_code", "")
        confidence = float(
            results.get("language_identification", [{}])[0].get("score", 0)
            if not expected_language
            else 1.0
        )

        return TranscriptionResult(
            text=full_text,
            segments=segments,
            language=detected_lang,
            confidence=confidence,
        )

    def __repr__(self) -> str:
        return f"<AWSTranscribeProvider region={self._region!r}>"
