import sys
sys.path.insert(0, ".")
import src.main
from src.api.router import api_router
routes = sorted(r.path for r in api_router.routes)
print("TOTAL", len(routes))
for p in routes:
    print(p)
