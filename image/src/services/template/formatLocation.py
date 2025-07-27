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
    
def format_place_name(place_names):
    if isinstance(place_names, list):
        if len(place_names) == 0:
            return ""
        elif len(place_names) == 1:
            return place_names[0]
        elif len(place_names) == 2:
            return f"{place_names[0]}和{place_names[1]}"
        else:
            return "、".join(place_names[:-1]) + f"和{place_names[-1]}"
    else:
        return place_names
        
def clean_za_prefix(sentence):
    """
    Cleans the "在" prefix from the beginning of a sentence and ensures it is only used once.
    """
    if sentence.startswith("在"):
        parts = sentence[1:].split("在")
        return "在" + "".join(parts)
    return sentence

def remove_repeated_place_name(text):
    """
    Removes repeated place names in the text, specifically for Taiwan and its cities.
    """
    return re.sub(r'(台灣|基隆市|新北市|臺北市)([^ ]*?)\1', r'\1\2', text)

def keep_suffix_only_on_last(loc_str: str, suffix: str = "下游", delimiter: str = "、") -> str:
    locs = loc_str.split(delimiter)
    for i in range(len(locs) - 1):
        if locs[i].endswith(suffix):
            locs[i] = locs[i].removesuffix(suffix)
    return delimiter.join(locs)