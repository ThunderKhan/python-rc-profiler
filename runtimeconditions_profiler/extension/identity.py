"""Helpers for exact extension release references and metadata."""

from __future__ import annotations


from ..errors import RuntimeConditionsError


def parse_identifier(reference: object) -> tuple[str, str]:
    """Read extension metadata or a string reference as (id, optional version)."""
    if isinstance(reference, str) and reference:
        marker = reference.rfind(":")
        scheme_end = reference.find("://")
        if marker > 0 and marker > scheme_end + 2 and marker > reference.rfind("/"):
            if marker == len(reference) - 1:
                raise RuntimeConditionsError("extension reference version suffix must be non-empty")
            return reference[:marker], reference[marker + 1 :]
        return reference, ""
    if not isinstance(reference, dict):
        raise RuntimeConditionsError("extension reference requires a non-empty string")
    identifier, version = reference.get("id"), reference.get("version", "")
    if not isinstance(identifier, str) or not identifier or ("version" in reference and (not isinstance(version, str) or not version)) or "uri" in reference:
        raise RuntimeConditionsError("extension metadata requires id and an optional string version; metadata.uri is unsupported")
    return identifier, version or ""


EXTENSION_FILENAME = "runtimeconditions.extension.yaml"


def short_identifier(identifier: str, version: str) -> str:
    """Drop the /<version>/runtimeconditions.extension.yaml tail of an https extension id.

    Ids that are not https URLs, or that do not end that way, stay unchanged.
    """
    tail = f"/{version}/{EXTENSION_FILENAME}"
    if version and identifier.startswith("https://") and identifier.endswith(tail):
        return identifier[: -len(tail)]
    return identifier


def profile_reference(reference: tuple[str, str]) -> str:
    """Serialize an extension reference for a Runtime Conditions Profile as <short-url>:<version>."""
    identifier, version = reference
    short = short_identifier(identifier, version)
    return f"{short}:{version}" if version else short


def definition_identifier(metadata: dict[str, object]) -> str:
    """Return the ID declared by valid extension metadata."""
    return parse_identifier(metadata)[0]

