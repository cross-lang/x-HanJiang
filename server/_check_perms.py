import sys
sys.path.insert(0, '.')
from src.infras.database import get_cached_database_provider
from sqlalchemy import text

s = get_cached_database_provider().get_session_factory()()
r = s.execute(text("""
    SELECT p.perm_code, p.perm_name
    FROM role_permissions rp
    JOIN permissions p ON rp.permission_id = p.id
    WHERE rp.role_id = 9
    ORDER BY p.id
"""))
rows = r.fetchall()
print(f"role_id=9 has {len(rows)} permissions:")
for row in rows:
    print(f"  {row[0]} - {row[1]}")

# 也查一下用户 id=2 的 role_id
r2 = s.execute(text("SELECT id, username, role_id FROM users WHERE id=2"))
for row in r2:
    print(f"\nuser id={row[0]}, username={row[1]}, role_id={row[2]}")

s.close()
