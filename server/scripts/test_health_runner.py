"""
Diagnostic and test execution script for verifying the server foundation and health endpoint.
"""

import sys
from pathlib import Path

print("Step 1: Setting sys.path...", flush=True)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("Step 2: Importing app from server.main...", flush=True)
from server.main import app
print("Step 3: Imported app successfully!", flush=True)

import asyncio
import httpx

async def run_async_tests():
    print("Step 4: Creating AsyncClient with ASGITransport...", flush=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print("Step 5: Client created. Requesting GET /...", flush=True)
        r_root = await client.get("/")
        print("Step 6: Root status:", r_root.status_code, r_root.json(), flush=True)
        assert r_root.status_code == 200

        print("Step 7: Requesting GET /api/v1/health...", flush=True)
        r_health = await client.get("/api/v1/health")
        print("Step 8: Health status:", r_health.status_code, r_health.json(), flush=True)
        assert r_health.status_code == 200

        body = r_health.json()
        assert body["success"] is True
        print("\n[ALL TESTS PASSED SUCCESSFULLY]", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        print("ERROR:", e, file=sys.stderr, flush=True)
        sys.exit(1)

