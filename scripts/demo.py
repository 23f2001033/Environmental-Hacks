"""Demo controls. Usage: python scripts/demo.py restart-demo | reset | seed | scale | status | links"""

import json
import sys
import time

from _common import api, outputs

cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
if cmd == "reset":
    print(api("/admin/reset", "POST", {}, admin=True))  # asynchronous: stops workflows, then deletes data
    for _ in range(40):
        time.sleep(5)
        stats = api("/stats")[1]
        if stats["cases"] == 0 and stats["villages"] == 0:
            print("reset done")
            break
    else:
        print("reset still running; check /stats")
elif cmd == "restart-demo":
    print(api("/admin/restart-demo", "POST", {}, admin=True))  # asynchronous
    time.sleep(25)
    print(json.dumps(api("/stats")[1]["by_status"]))
elif cmd == "seed":
    print(api("/admin/ingest", "POST", {"source": "fixtures"}, admin=True))
    time.sleep(20)
    print(json.dumps(api("/stats")[1]["by_status"]))
elif cmd == "scale":
    print(api("/admin/scale-run", "POST", {}, admin=True))
    while True:
        time.sleep(30)
        stats = api("/stats")[1]
        sc, run = stats.get("scale_run"), stats.get("last_run") or {}
        print(time.strftime("%H:%M:%S"), "cases", stats["cases"], "by_status", json.dumps(stats["by_status"]),
              "scale", json.dumps(sc))
        if sc and sc["status"] != "RUNNING":
            print(json.dumps({"alert_latency": stats["alert_latency"], "run": {k: run.get(k) for k in (
                "new_cases", "villages", "villages_located", "geocode_calls", "seconds", "cost_estimate")}}, indent=1))
            break
elif cmd == "status":
    print(json.dumps(api("/stats")[1], ensure_ascii=False, indent=1))
elif cmd == "links":
    bot = api("/health")[1]["bot"]
    print("Test console:", outputs()["TestUiUrl"])
    for v in api("/villages")[1]["villages"]:
        print(f"{v['name']:22} village: https://t.me/{bot}?start=v_{v['key']}")
    print("Engineer, Harpalpur block:", f"https://t.me/{bot}?start=e_5037")
    print("Engineer, Anta block (Baran):", f"https://t.me/{bot}?start=e_4320")
else:
    sys.exit(__doc__)
