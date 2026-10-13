"""
TexturepackUpscaler - Core Module
"""
from .algorithms import (
    scale2x_epx,
    scale3x_epx,
    scale4x_epx,
    nearest_neighbor,
    lanczos_upscale,
    bicubic_upscale,
    AVAILABLE_ALGORITHMS,
    upscale_image_array
)
from .processor import ResourcePackProcessor, ProcessingStats, ProgressCallback

__all__ = [
    "scale2x_epx",
    "scale3x_epx",
    "scale4x_epx",
    "nearest_neighbor",
    "lanczos_upscale",
    "bicubic_upscale",
    "AVAILABLE_ALGORITHMS",
    "upscale_image_array",
    "ResourcePackProcessor",
    "ProcessingStats",
    "ProgressCallback",
]
