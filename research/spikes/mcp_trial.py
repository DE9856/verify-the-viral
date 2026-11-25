"""Minimal MCP (streamable HTTP) client for the DetectifAI trial endpoint.
Usage: python mcp_trial.py list
       python mcp_trial.py detect <file> [<file> ...]   (each file = 1 trial check)
"""
import base64, json, sys, time, pathlib
import httpx

URL = "https://platform.detectif.ai/mcp/trial"
H = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def parse(resp):
    ct = resp.headers.get("content-type", "")
    if "text/event-stream" in ct:
        out = None
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                out = json.loads(line[5:].strip())
        return out
    return resp.json()


def main():
    c = httpx.Client(timeout=300)
    r = c.post(URL, headers=H, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke-test", "version": "0.1"}}})
    r.raise_for_status()
    h = dict(H)
    sid = r.headers.get("mcp-session-id")
    if sid:
        h["Mcp-Session-Id"] = sid
    init = parse(r)
    c.post(URL, headers=h, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    if sys.argv[1] == "list":
        print("server:", init.get("result", {}).get("serverInfo"))
        tools = parse(c.post(URL, headers=h, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
        for t in tools["result"]["tools"]:
            print("-", t["name"], json.dumps(t.get("inputSchema", {}).get("properties", {}))[:300])
        return
    for i, f in enumerate(sys.argv[2:]):
        p = pathlib.Path(f)
        t0 = time.time()
        r = c.post(URL, headers=h, json={"jsonrpc": "2.0", "id": 10 + i, "method": "tools/call", "params": {
            "name": "detect_deepfake",
            "arguments": {"audio_base64": base64.b64encode(p.read_bytes()).decode(), "filename": p.name}}})
        res = parse(r)
        dt = time.time() - t0
        pathlib.Path("results").mkdir(exist_ok=True)
        pathlib.Path("results", p.stem + ".json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        print(f"== {p.name}  ({dt:.1f}s round trip)")
        print(json.dumps(res, ensure_ascii=False)[:1500])


main()
