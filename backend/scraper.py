import logging
from typing import Optional, Dict, Any
import trafilatura

logger = logging.getLogger("amber.scraper")


def extract_url_content(url: str) -> Optional[Dict[str, Any]]:
    """
    Downloads and extracts clean readable text and metadata from a web page.
    Strips ads, boilerplate, navigation, and comments.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Could not fetch content from {url}")
            return None
        
        extracted_text = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            include_tables=True,
            output_format="txt",
            favor_precision=True
        )
        
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else None
        description = metadata.description if metadata and metadata.description else None
        
        return {
            "title": title,
            "description": description,
            "content": extracted_text or "",
        }
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None
