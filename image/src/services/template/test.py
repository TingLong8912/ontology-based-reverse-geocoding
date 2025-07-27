import re
from collections import defaultdict

def format_locations(locations, level="township"):
    """
    Formats a list of county, town and village names into a readable string grouped by county.
    """
    if not locations:
        return ""

    locations = [loc.replace("在", "") for loc in locations]

    grouped = defaultdict(list)
    for loc in locations:
        match = re.match(r"^.{2,4}[市縣]", loc)
        if match:
            prefix = match.group()
            suffix = loc.replace(prefix, "")
            grouped[prefix].append(suffix)
        else:
            grouped[""].append(loc)
            
    segments = []
    for prefix, suffixes in grouped.items():
        if not suffixes:
            segments.append(prefix)
        elif len(suffixes) == 1:
            segments.append(f"{prefix}{suffixes[0]}")
        else:
            display_suffixes = suffixes[:3]
            if len(display_suffixes) == 2:
                body = "和".join(display_suffixes)
            else:
                body = "、".join(display_suffixes[:-1]) + "和" + display_suffixes[-1]
            if len(suffixes) > 3:
                body += "等地"
            segments.append(f"{prefix}{body}")

    if not segments:
        return ""
    elif len(segments) == 1:
        return "在" + segments[0]
    else:
        return "在" + "，以及".join(segments[:-1]) + "，以及" + segments[-1]

print(format_locations(['新北市石碇區', '新北市中和區', '新北市板橋區', '新北市永和區', '臺北市文山區', '臺北市中正區', '新北市新店區']))