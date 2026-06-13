from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Lead:
    """Represents a qualified LinkedIn lead who is open to work."""

    full_name: str
    headline: str
    company_name: str
    city: str
    country: str
    url: str
    open_to_work: bool

    # Optional enrichment fields
    profile_id: Optional[str] = field(default=None)
    connections: Optional[int] = field(default=None)
    summary: Optional[str] = field(default=None)
    email: Optional[str] = field(default=None)

    @classmethod
    def from_enrichment(cls, data: dict) -> "Lead":
        """
        Construct a Lead from the raw dict returned by the
        anchor/linkedin-profile-enrichment actor.
        Missing fields fall back to empty strings / False.
        """
        return cls(
            full_name=data.get("full_name") or data.get("name") or "Unknown",
            headline=data.get("headline") or "",
            company_name=data.get("company_name") or data.get("company") or "",
            city=data.get("city") or "",
            country=data.get("country") or "",
            url=data.get("url") or data.get("linkedInUrl") or "",
            open_to_work=bool(data.get("open_to_work", False)),
            profile_id=data.get("profile_id") or data.get("id"),
            connections=data.get("connections"),
            summary=data.get("summary"),
        )

    @property
    def location(self) -> str:
        """Human-readable location string."""
        parts = [p for p in (self.city, self.country) if p]
        return ", ".join(parts) if parts else "Unknown"

    def __str__(self) -> str:
        return (
            f"Name: {self.full_name}\n"
            f"Headline: {self.headline}\n"
            f"Company: {self.company_name}\n"
            f"Location: {self.location}\n"
            f"Email: {self.email or 'Not found'}\n"
            f"URL: {self.url}"
        )