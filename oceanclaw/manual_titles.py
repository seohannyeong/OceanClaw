"""Attach PDF outline titles without changing chunk bodies or identifiers."""
from collections import defaultdict

def compact(text):
    positions = [i for i, c in enumerate(text) if c.isalnum()]
    return "".join(text[i].lower() for i in positions), positions


def bookmarks(reader):
    def walk(items, parents=()):
        previous = parents
        for item in items:
            if isinstance(item, list):
                yield from walk(item, previous)
            else:
                previous = (*parents, item.title)
                yield {"page": reader.get_destination_page_number(item) + 1, "path": list(previous)}
    return list(walk(reader.outline))


def annotate(pages, chunks, headings):
    by_page = defaultdict(list)
    for heading in headings:
        by_page[heading["page"]].append(heading)
    spans = {}
    missing = []
    active = None
    for page in pages:
        key = (page["source"], page["page"])
        text = page["text"]
        flat, offsets = compact(text)
        anchors = {}
        for h in by_page[page["page"]]:
            needle, _ = compact(h["path"][-1])
            at = flat.find(needle) if needle else -1
            if at < 0:
                missing.append(h)
                continue
            start = offsets[at]
            if start not in anchors or len(anchors[start]["path"]) < len(h["path"]):
                anchors[start] = {"id": f"{page['source']}:p{page['page']}:{start}", "path": h["path"]}
        # Missing headings mean continuation cannot be assigned confidently.
        if any(h["page"] == page["page"] for h in missing):
            active = None
        cursor = 0
        parts = []
        for start, heading in sorted(anchors.items()):
            if start > cursor:
                parts.append({"start": cursor, "end": start, "section": active})
            cursor, active = start, heading
        parts.append({"start": cursor, "end": len(text), "section": active})
        spans[key] = parts
    page_map = {(p["source"], p["page"]): p["text"] for p in pages}
    previous_starts = defaultdict(lambda: -1)
    enriched = []
    for chunk in chunks:
        key = (chunk["source"], chunk["page"])
        text = page_map[key]
        flat, offsets = compact(text)
        needle, _ = compact(chunk["text"])
        start_search = previous_starts[key] + 1
        at = flat.find(needle, start_search)
        if at < 0:
            raise ValueError(f"Cannot align frozen chunk: {chunk['chunk_id']}")
        previous_starts[key] = at
        start, end = offsets[at], offsets[at + len(needle) - 1] + 1
        pieces = []
        for span in spans[key]:
            left, right = max(start, span["start"]), min(end, span["end"])
            if left < right and span["section"]:
                pieces.append({"section_id": span["section"]["id"], "title_path": span["section"]["path"],
                    "start": left, "end": right, "text": text[left:right]})
        titles = list(dict.fromkeys(" > ".join(p["title_path"]) for p in pieces))
        prefix = "\n".join(titles)
        enriched.append({**chunk, "sections": pieces, "embedding_text": f"{prefix}\n\n{chunk['text']}" if prefix else chunk["text"]})
    return enriched, missing
