# app/__init__.py
# Reddit Digest - AI-powered Reddit summarizer

__version__ = "0.2.0"
__app_name__ = "Reddit Digest"

from .config import APP_NAME, APP_VERSION

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "__version__",
    "__app_name__",
]
