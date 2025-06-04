def ToFullText(locd_result):
    """
    This function takes the location description json result and converts it into a full text format.
    """

    full_text = {}

    for entry in locd_result:
        qualities = entry.get("Qualities")
        if qualities is None or not isinstance(qualities, dict):
            print(f"Warning: entry has no valid 'Qualities': {entry}")
            continue

        typology_keys = [k for k in qualities.keys() if "Typology" in k]
        if not typology_keys:
            print(f"Warning: no Typology key found in qualities: {qualities}")
            continue

        typology = typology_keys[0].split("_")[-1]

        if typology not in full_text:
            full_text[typology] = []

        spatial_preposition = entry.get('SpatialPreposition', '')
        place_name = entry.get('PlaceName', '')
        localisers = entry.get('Localiser', [])
        spatial_preposition_class = entry.get('SpatialPrepositionClass', None)
        localiser_class = entry.get('LocaliserClass', None)

        if localisers == [] or localisers is None:
            localiser = ''
            full_text[typology].append(f"{spatial_preposition}{place_name}{localiser}")
        else:
            for localiser in localisers:
                full_text[typology].append(f"{spatial_preposition}{place_name}{localiser}")

    for typology in full_text:
        full_text[typology] = list(set(full_text[typology]))

    # New logic: build converted_full_text with SpatialPrepositionClass and LocaliserClass
    converted_full_text = []
    for entry in locd_result:
        qualities = entry.get("Qualities", {})
        typology = [k for k in qualities.keys() if "Typology" in k][0].split("_")[-1]
        spatial_preposition = entry.get("SpatialPreposition") or ""
        place_name = entry.get("PlaceName") or ""
        localisers = entry.get("Localiser") or []
        spatial_preposition_class = entry.get("SpatialPrepositionClass", None)
        localiser_class = entry.get("LocaliserClass", None)

        if not localisers:
            full_text_item = {
                "text": f"{spatial_preposition}{place_name}",
                "type": typology,
                "PlaceName": place_name,
                "SpatialPrepositionClass": spatial_preposition_class,
                "SpatialPreposition": spatial_preposition,
                "LocaliserClass": None,
                "Localiser": "",
            }
            converted_full_text.append(full_text_item)
        else:
            for localiser in localisers:
                full_text_item = {
                    "text": f"{spatial_preposition}{place_name}{localiser}",
                    "type": typology,
                    "PlaceName": place_name,
                    "SpatialPrepositionClass": spatial_preposition_class,
                    "SpatialPreposition": spatial_preposition,
                    "LocaliserClass": localiser_class,
                    "Localiser": localiser
                }
                converted_full_text.append(full_text_item)

    seen = set()
    unique_items = []
    for item in converted_full_text:
        key = f"{item['SpatialPreposition']}_{item['PlaceName']}_{item['Localiser']}"
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return unique_items
