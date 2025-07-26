from services.template.formatLocation import format_place_name

def ToFullText(locd_result):
    """
    This function takes the location description json result and converts it into a full text format.
    """
    converted_full_text = []
    for entry in locd_result:
        qualities = entry.get("Qualities", {})
        qualitiesSR = entry.get("QualitiesSR", {})
        typology = [k for k in qualities.keys() if "Typology" in k][0].split("_")[-1]
        spatial_preposition = entry.get("SpatialPreposition") or ""
        place_name = format_place_name(entry.get("PlaceName") or "")
        localiser = entry.get("Localiser") or ""
        spatial_preposition_class = entry.get("SpatialPrepositionClass", None)
        localiser_class = entry.get("LocaliserClass", None)

        if localiser == "":
            full_text_item = {
                "text": f"{spatial_preposition}{place_name}",
                "type": typology,
                "PlaceName": place_name,
                "SpatialPrepositionClass": spatial_preposition_class,
                "SpatialPreposition": spatial_preposition,
                "LocaliserClass": None,
                "Localiser": "",
                "QualitiesSR": qualitiesSR if qualitiesSR else None
            }
            converted_full_text.append(full_text_item)
        else:
            full_text_item = {
                "text": f"{spatial_preposition}{place_name}{localiser}",
                "type": typology,
                "PlaceName": place_name,
                "SpatialPrepositionClass": spatial_preposition_class,
                "SpatialPreposition": spatial_preposition,
                "LocaliserClass": localiser_class,
                "Localiser": localiser,
                "QualitiesSR": qualitiesSR if qualitiesSR else None
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
