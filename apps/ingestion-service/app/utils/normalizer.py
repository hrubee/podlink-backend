from typing import Dict, Any
from app.models.metadata import PodcastMetadata, SocialLinkSchema

class PodcastNormalizer:
    @staticmethod
    def normalize_podchaser_podcast(raw_data: Dict[str, Any]) -> PodcastMetadata:
        """Maps Podchaser GraphQL response to internal PodcastMetadata model."""
        pod = raw_data.get("podcast", {})
        
        # Normalize social links from the nested object
        socials = []
        raw_socials = pod.get("socialLinks", {})
        if raw_socials:
            for platform, url in raw_socials.items():
                if url:
                    socials.append(SocialLinkSchema(
                        url=url,
                        platform_type=platform
                    ))

        return PodcastMetadata(
            external_id=pod.get("id", "unknown"),
            title=pod.get("title", "Untitled"),
            description=pod.get("description"),
            rating=float(pod.get("ratingAverage") or 0.0),
            categories=[c["title"] for c in pod.get("categories", []) if "title" in c],
            social_links=socials
        )
