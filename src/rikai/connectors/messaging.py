"""
Messaging utilities for Telegram and Slack connectors.

Provides image description and message preparation for Tama.
This module acts as "Tama's eyes" - processing images before
they reach Letta (which is text-only).
"""

import base64
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProcessedMessage:
    """A message processed and ready for Tama."""

    text: str
    platform: str
    sender: str
    metadata: dict[str, Any]


async def describe_image(
    image_bytes: bytes,
    media_type: str = "image/png",
    context: str | None = None,
) -> str:
    """
    Use Claude Vision to describe an image.

    This is "Tama's eyes" - converting visual input to text
    that can be processed by Letta.

    Args:
        image_bytes: Raw image data
        media_type: MIME type (image/png, image/jpeg, etc.)
        context: Optional context about where the image came from

    Returns:
        Text description of the image
    """
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Install with: pip install anthropic"
        )

    client = anthropic.Anthropic()

    # Build the prompt
    prompt = "Describe what this image shows. Be concise but capture the key details."
    if context:
        prompt = f"{prompt} Context: {context}"

    # Encode image
    image_data = base64.b64encode(image_bytes).decode()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Image description failed: {e}")
        return "[Unable to process image]"


async def prepare_message_for_tama(
    text: str | None = None,
    image_bytes: bytes | None = None,
    image_media_type: str = "image/png",
    image_caption: str | None = None,
    platform: str = "unknown",
    sender: str = "unknown",
) -> ProcessedMessage:
    """
    Prepare a message (text and/or image) for Tama.

    Converts images to descriptions so they can be understood
    by Letta's text-based message API.

    Args:
        text: Optional text content
        image_bytes: Optional image data
        image_media_type: MIME type of image
        image_caption: Optional caption provided with image
        platform: Source platform (telegram, slack)
        sender: Who sent the message

    Returns:
        ProcessedMessage ready for Tama
    """
    metadata = {
        "platform": platform,
        "sender": sender,
        "has_image": image_bytes is not None,
    }

    # Text only
    if not image_bytes:
        return ProcessedMessage(
            text=text or "",
            platform=platform,
            sender=sender,
            metadata=metadata,
        )

    # Image (with optional text)
    context = f"From {platform}, sent by {sender}"
    if image_caption:
        context += f". Caption: {image_caption}"

    description = await describe_image(
        image_bytes,
        media_type=image_media_type,
        context=context,
    )

    # Format message for Tama
    if text:
        formatted_text = f"[User sent an image: {description}]\n\nThey also wrote: {text}"
    else:
        formatted_text = f"[User sent an image: {description}]"

    metadata["image_description"] = description

    return ProcessedMessage(
        text=formatted_text,
        platform=platform,
        sender=sender,
        metadata=metadata,
    )


def get_media_type(filename: str | None) -> str:
    """Get MIME type from filename extension."""
    if not filename:
        return "image/png"

    ext = filename.lower().split(".")[-1]
    types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return types.get(ext, "image/png")
