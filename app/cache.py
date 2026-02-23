# app/cache.py
# Simple caching system to reduce API calls and costs

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

# Cache directory
CACHE_DIR = Path.home() / ".reddit_digest" / "cache"


def ensure_cache_dir():
    """Ensure the cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(query_type: str, **params) -> str:
    """Generate a unique cache key from query parameters."""
    # Sort params for consistent hashing
    sorted_params = sorted(params.items())
    param_str = f"{query_type}:{sorted_params}"
    return hashlib.md5(param_str.encode()).hexdigest()


def get_cache_path(cache_key: str) -> Path:
    """Get the file path for a cache key."""
    return CACHE_DIR / f"{cache_key}.json"


def is_cache_valid(cache_path: Path, max_age_hours: int = 1) -> bool:
    """Check if a cache file exists and is still valid."""
    if not cache_path.exists():
        return False
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cached_time = datetime.fromisoformat(data.get('timestamp', '1970-01-01'))
        age = datetime.now() - cached_time
        
        return age < timedelta(hours=max_age_hours)
    except Exception:
        return False


def get_cached(query_type: str, max_age_hours: int = 1, **params) -> Optional[Any]:
    """Get cached data if available and valid."""
    cache_key = get_cache_key(query_type, **params)
    cache_path = get_cache_path(cache_key)
    
    if not is_cache_valid(cache_path, max_age_hours):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('data')
    except Exception:
        return None


def set_cached(data: Any, query_type: str, **params) -> bool:
    """Cache data with the given parameters."""
    try:
        ensure_cache_dir()
        cache_key = get_cache_key(query_type, **params)
        cache_path = get_cache_path(cache_key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'query_type': query_type,
            'params': params,
            'data': data
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Warning: Could not cache data: {e}")
        return False


def clear_cache() -> int:
    """Clear all cached data. Returns number of files deleted."""
    count = 0
    try:
        if CACHE_DIR.exists():
            for cache_file in CACHE_DIR.glob("*.json"):
                cache_file.unlink()
                count += 1
    except Exception as e:
        print(f"Warning: Error clearing cache: {e}")
    return count


def get_cache_stats() -> dict:
    """Get statistics about the cache."""
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'oldest_file': None,
        'newest_file': None
    }
    
    try:
        if CACHE_DIR.exists():
            files = list(CACHE_DIR.glob("*.json"))
            stats['total_files'] = len(files)
            
            for f in files:
                stats['total_size_bytes'] += f.stat().st_size
                
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if stats['oldest_file'] is None or mtime < stats['oldest_file']:
                    stats['oldest_file'] = mtime
                if stats['newest_file'] is None or mtime > stats['newest_file']:
                    stats['newest_file'] = mtime
    except Exception:
        pass
    
    return stats
