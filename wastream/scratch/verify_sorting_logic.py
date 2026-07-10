# Verify sorting: torrent_first should promote torrents above DDL even with different resolution

results = [
    {"model_type": "link",    "display_name": "Film.2023.4K.WEB-DL.MULTI",    "resolution": 0, "cache_status": "cached"},
    {"model_type": "torrent", "display_name": "Film.2023.1080p.BluRay.MULTI",  "resolution": 1, "cache_status": "cached"},
    {"model_type": "link",    "display_name": "Film.2023.1080p.WEB-DL.VOSTFR","resolution": 1, "cache_status": "cached"},
    {"model_type": "torrent", "display_name": "Film.2023.720p.WEB-DL.VOSTFR", "resolution": 2, "cache_status": "cached"},
]

for pref_label, pref in [("ddl_first", "ddl_first"), ("torrent_first", "torrent_first")]:
    print(f"\n=== stream_type_preference = {pref_label} ===")

    streams = []
    for r in results:
        is_torrent = (r["model_type"] == "torrent")
        if pref == "torrent_first":
            stream_type_priority = 0 if is_torrent else 1
        else:
            stream_type_priority = 1 if is_torrent else 0

        streams.append({
            "display_name": r["display_name"],
            "model_type": r["model_type"],
            "_sort_values": {
                "cached":      0 if r["cache_status"] == "cached" else 1,
                "resolution":  r["resolution"],
                "size":        0,
                "release_type": 0,
                "language":    (0, 0, "French"),
                "stream_type": stream_type_priority,
            },
        })

    default_sort_order = ["cached", "resolution", "size", "release_type", "language", "stream_type"]
    sort_order = list(default_sort_order)  # user didn't customize

    # Apply the fix: auto-promote stream_type when preference is non-default
    if pref != "ddl_first" and "stream_type" in sort_order:
        st_idx = sort_order.index("stream_type")
        cached_idx = sort_order.index("cached") if "cached" in sort_order else -1
        if st_idx > (cached_idx + 1):
            sort_order.pop(st_idx)
            sort_order.insert(cached_idx + 1, "stream_type")

    print(f"  Effective sort_order: {sort_order}")
    streams.sort(key=lambda s: tuple(s["_sort_values"][k] for k in sort_order))
    for s in streams:
        print(f"  [{s['model_type']:<7}] {s['display_name']}")
