import re

def format_locations(locations, level="township"):
    """
    Formats a list of county, town and village names into a readable string based on the specified level.
    """
    if not locations:
        return ""

    locations = [loc.replace("在", "") for loc in locations]

    if level == "township":
        prefix = locations[0][:3]
        main = locations[0]
        shortened = [loc.replace(prefix, "") if loc.startswith(prefix) else loc for loc in locations[1:]]
    elif level == "village":
        prefix_match = re.match(r"^.{3}.{2,3}區", locations[0])
        prefix = prefix_match.group() if prefix_match else ""
        main = locations[0]
        shortened = [loc.replace(prefix, "") if loc.startswith(prefix) else loc for loc in locations[1:]]
    else:
        return "不支援的層級"

    if not shortened:
        return "在" + main
    elif len(shortened) == 1:
        return "在" + main + "和" + shortened[0]
    else:
        return "在" + main + "、" + "、".join(shortened[:-1]) + "和" + shortened[-1]
    
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
