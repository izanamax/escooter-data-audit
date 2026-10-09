"""A dependency-free audit of COCO detection annotations and dataset splits."""

__version__ = "1.0.0"

from .audit import audit_splits

__all__ = ["audit_splits", "__version__"]
