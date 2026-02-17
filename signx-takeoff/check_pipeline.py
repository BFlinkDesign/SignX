import os, requests, json

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
if not NOTION_TOKEN:
    raise RuntimeError("Set NOTION_TOKEN environment variable")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

r = requests.post(
    "https://api.notion.com/v1/databases/304c1e58d2dd814aae63c6a0d44e6679/query",
    headers=headers,
    json={"sorts":[{"timestamp":"last_edited_time","direction":"descending"}],"page_size":25}
)

for entry in r.json().get("results", []):
    props = entry["properties"]
    title = ""
    status = ""
    for k, v in props.items():
        if v.get("type") == "title" and v.get("title"):
            title = v["title"][0].get("plain_text", "")
        if v.get("type") == "select" and v.get("select"):
            if "status" in k.lower() or "stage" in k.lower():
                status = v["select"]["name"]
    if title:
        print(f"{status:25s} | {title}")
