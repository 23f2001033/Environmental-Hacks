"""Demo controls. Usage: python scripts/demo.py reset | seed | status | links"""

import json
import sys
import time

from _common import api, outputs

cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
if cmd == "reset":
    print(api("/admin/reset", "POST", {}, admin=True))
elif cmd == "seed":
    print(api("/admin/ingest", "POST", {"source": "fixtures"}, admin=True))
    time.sleep(20)
    print(json.dumps(api("/stats")[1]["by_status"]))
elif cmd == "status":
    print(json.dumps(api("/stats")[1], ensure_ascii=False, indent=1))
elif cmd == "links":
    bot = api("/health")[1]["bot"]
    print("Test console:", outputs()["TestUiUrl"])
    for v in api("/villages")[1]["villages"]:
        print(f"{v['name']:22} village: https://t.me/{bot}?start=v_{v['key']}")
    print("Engineer, Harpalpur block:", f"https://t.me/{bot}?start=e_5037")
    print("Engineer, Anta block (Baran):", f"https://t.me/{bot}?start=e_27-baran-anta")
else:
    sys.exit(__doc__)
