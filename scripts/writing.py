#!/usr/bin/env python3
"""Write the latest posts from screenager.dev's feed into README.md.

usage: writing.py [README.md] [count]

Replaces the lines between <!-- writing:start --> and <!-- writing:end -->.
Standard library only, so the workflow needs nothing installed. Exits 0 without
touching the file when the feed is unreachable, so a flaky night keeps the
last good list.
"""
import email.utils, pathlib, re, sys, urllib.request
import xml.etree.ElementTree as ET

FEED = "https://screenager.dev/rss.xml"
readme = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")
count = int(sys.argv[2]) if len(sys.argv) > 2 else 4

try:
    with urllib.request.urlopen(FEED, timeout=20) as r:
        root = ET.fromstring(r.read())
except Exception as e:  # noqa: BLE001 - any failure means "try again tomorrow"
    print(f"writing: feed unavailable ({e}); leaving README as is")
    sys.exit(0)

posts = []
for item in root.iter("item"):
    title, link = item.findtext("title", "").strip(), item.findtext("link", "").strip()
    date = email.utils.parsedate_to_datetime(item.findtext("pubDate", ""))
    if title and link:
        posts.append((date, title, link))
posts.sort(key=lambda p: p[0], reverse=True)  # stable: same-day posts keep the feed order

# one line each, the year as a mono stamp, like the site's margin list
lines = [f"`{d.year}`&nbsp; [{t}]({l})" for d, t, l in posts[:count]]
lines = [line + "<br>" for line in lines[:-1]] + lines[-1:]
text = readme.read_text()
new = re.sub(r"(<!-- writing:start -->\n)(?:.*?\n)?(<!-- writing:end -->)",
             lambda m: m.group(1) + "".join(line + "\n" for line in lines) + m.group(2), text, flags=re.S)
if new != text:
    readme.write_text(new)
    print(f"writing: {len(lines)} posts")
