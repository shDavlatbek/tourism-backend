import base64
import hashlib
import hmac
from typing import Optional, Dict, Any
from urllib.parse import quote
from django.conf import settings


class SimpleImgproxyUrlBuilder:
    """
    Simple imgproxy URL builder for insecure mode.
    Generates URLs in format: /insecure/processing_options/plain/source_url
    
    This is for frontend-direct usage where the frontend constructs URLs.
    Example: https://ipx.lamenu.uz/insecure/rs:fit:128:128:0/q:100/plain/https://cdn.lamenu.uz/image.jpg
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or getattr(settings, 'IMGPROXY_BASE_URL', 'http://localhost:8080')).rstrip('/')
        
    def build_url(
        self,
        source_url: str,
        resize: str = None,
        width: int = None,
        height: int = None,
        resize_type: str = 'fit',
        enlarge: bool = False,
        quality: int = None,
        format: str = None,
        **kwargs
    ) -> str:
        """
        Build imgproxy URL in insecure mode.
        
        Args:
            source_url: Source image URL
            resize: Custom resize string (e.g., "rs:fit:128:128:0")
            width: Image width
            height: Image height
            resize_type: fit, fill, crop, force
            enlarge: Allow enlargement (0 or 1)
            quality: Image quality (1-100)
            format: Output format (webp, jpg, png, avif)
            **kwargs: Additional processing options
            
        Returns:
            Complete imgproxy URL
        """
        options = []
        
        # Resize option
        if resize:
            options.append(resize)
        elif width or height:
            w = width or 0
            h = height or 0
            enlarge_flag = 1 if enlarge else 0
            options.append(f"rs:{resize_type}:{w}:{h}:{enlarge_flag}")
        
        # Quality
        if quality:
            options.append(f"q:{quality}")
            
        # Format
        if format:
            options.append(f"f:{format}")
            
        # Additional options
        for key, value in kwargs.items():
            if value is not None:
                options.append(f"{key}:{value}")
        
        # Build URL
        processing_options = "/".join(options) if options else ""
        url_parts = [self.base_url, "insecure"]
        
        if processing_options:
            url_parts.append(processing_options)
            
        url_parts.extend(["plain", source_url])
        
        return "/".join(url_parts)


# Global instance
imgproxy = SimpleImgproxyUrlBuilder()


# Convenience functions for common use cases
def build_imgproxy_url(source_url: str, **kwargs) -> str:
    """Build imgproxy URL with options."""
    return imgproxy.build_url(source_url, **kwargs)


def get_thumbnail_url(source_url: str, size: int = 200, quality: int = 85) -> str:
    """Get square thumbnail URL."""
    return imgproxy.build_url(
        source_url,
        width=size,
        height=size,
        resize_type='fill',
        quality=quality
    )


def get_responsive_url(source_url: str, width: int, quality: int = 85) -> str:
    """Get responsive image URL for specific width."""
    return imgproxy.build_url(
        source_url,
        width=width,
        resize_type='fit',
        quality=quality
    )


# Preset configurations for common sizes
PRESET_SIZES = {
    'thumb_small': {'width': 150, 'height': 150, 'resize_type': 'fill'},
    'thumb_medium': {'width': 300, 'height': 300, 'resize_type': 'fill'},
    'thumb_large': {'width': 500, 'height': 500, 'resize_type': 'fill'},
    'list_small': {'width': 200, 'height': 150, 'resize_type': 'fill'},
    'list_medium': {'width': 400, 'height': 300, 'resize_type': 'fill'},
    'banner_mobile': {'width': 768, 'height': 400, 'resize_type': 'fill'},
    'banner_desktop': {'width': 1920, 'height': 600, 'resize_type': 'fill'},
    'avatar_small': {'width': 100, 'height': 100, 'resize_type': 'fill'},
    'avatar_medium': {'width': 200, 'height': 200, 'resize_type': 'fill'},
}


def get_preset_url(source_url: str, preset: str, quality: int = 85) -> str:
    """Get URL using predefined preset."""
    if preset not in PRESET_SIZES:
        raise ValueError(f"Unknown preset: {preset}")
    
    options = PRESET_SIZES[preset].copy()
    options['quality'] = quality
    
    return imgproxy.build_url(source_url, **options) 