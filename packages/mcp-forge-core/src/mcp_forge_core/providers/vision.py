"""Vision provider base class for mcp-forge.

Defines the interface for structured data extraction from images.
Subclass BaseVisionProvider and implement the abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VisionExtractionResult:
    """Result of a structured extraction from an image.

    Attributes:
        extraction_type: Label describing the extraction performed.
        data: Extracted key-value data.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        raw_text: Optional raw text output from the model.
    """

    extraction_type: str
    data: dict[str, Any]
    input_tokens: int
    output_tokens: int
    raw_text: str = ""


class BaseVisionProvider(ABC):
    """Base class for vision extraction backends.

    Subclass and implement :meth:`extract_structured` and :meth:`get_supported_types`
    to integrate any vision model. The extraction types are entirely defined
    by your implementation — the framework imposes no domain assumptions.

    Example::

        class ProductVisionProvider(BaseVisionProvider):
            async def extract_structured(self, image_data, extraction_type, **kwargs):
                ...
            def get_supported_types(self):
                return ["product_label", "barcode", "shelf_layout"]
    """

    @abstractmethod
    async def extract_structured(
        self,
        image_data: bytes,
        extraction_type: str,
        *,
        custom_fields: list[str] | None = None,
        language_hint: str | None = None,
    ) -> VisionExtractionResult:
        """Extract structured data from an image.

        Args:
            image_data: Raw image bytes (PNG, JPEG, etc.).
            extraction_type: What to extract — defined by your implementation.
            custom_fields: Optional list of specific fields to extract.
            language_hint: Optional language hint for OCR/extraction.

        Returns:
            VisionExtractionResult with extracted data.
        """
        ...

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """Return the list of extraction types this provider supports."""
        ...
