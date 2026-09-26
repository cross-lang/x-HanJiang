import sys
sys.path.insert(0, '.')
from src.infras.cache import get_cached_cache_provider

provider = get_cached_cache_provider()
# 清掉所有权限缓存
keys = provider._redis.keys("perm:*")
if keys:
    provider._redis.delete(*keys)
    print(f"cleared {len(keys)} permission cache keys")
else:
    print("no permission cache keys")
