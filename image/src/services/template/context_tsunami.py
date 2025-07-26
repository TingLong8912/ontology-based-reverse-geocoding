from services.template.calculate_quality import average_quality
from services.template.retrieveLocationInfo import retrieve_location_info
from services.template.formatLocation import clean_za_prefix, remove_repeated_place_name

def generate_tsunami_descriptions(onto, timestamp, w1, w2):
    loc_to_info = retrieve_location_info(onto[timestamp])

    combinations = {
        'combination': [],
        'avg_quality': []
    }

    qualities_to_check = ["Scale", "Prominence"]
    out_localisers = {"OpenSeaLocaliser", "OffshoreLocaliser", "ShoreLocaliser"}
    part_localisers = {
        "MidLandLocaliser", "NorthernPartLocaliser", "SouthernPartLocaliser", "EastPartLocaliser", "WesternPartLocaliser", "NortheastLocaliser", "SoutheastLocaliser",
        "MidnorthLocaliser", "MidsouthLocaliser", "MidwestLocaliser", "NortheastPartLocaliser", "SoutheastPartLocaliser", "NorthwestPartLocaliser", "SouthwestPartLocaliser"
    }
    coastlines_out_locs = [
        loc for loc, info in loc_to_info.items()
        if "CoastLine" in info.get("typologies", [])
        and any(l in out_localisers for l in info.get("localisers", []))
    ]
    coastlines_part_locs = [
        loc for loc, info in loc_to_info.items()
        if "CoastLine" in info.get("typologies", [])
        and any(l in part_localisers for l in info.get("localisers", []))
    ]

    nearshores_locs = [loc for loc, info in loc_to_info.items() if "Nearshore" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    sea_locs = [loc for loc, info in loc_to_info.items() if "Sea" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    counties_locs = [loc for loc, info in loc_to_info.items() if "CountiesBoundary" in info["typologies"] and not info["spatialPrepositions"] ]

    if len(nearshores_locs) > 0:
        for nearshore in nearshores_locs:
            elements = [nearshore]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(nearshore)
    if len(sea_locs) > 0:
        for sea in sea_locs:
            elements = [sea]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(sea)
    if len(coastlines_out_locs) > 0 or len(coastlines_part_locs) > 0:
        for coastline in coastlines_out_locs:
            for part_coastline in coastlines_part_locs:
                elements = [coastline, part_coastline]
                avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                sentence = f"{part_coastline}{coastline}"
                combinations["avg_quality"].append(avg_qualities)
                combinations["combination"].append(sentence)
    if len(counties_locs) > 0:
        for county in counties_locs:
            elements = [county]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(county)

    top_n = 5  
    combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))
    combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
    top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]
    top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
    top_descriptions = [remove_repeated_place_name(desc) for desc in top_descriptions]

    # Clear the ontology
    onto[timestamp].destroy(update_relation = True, update_is_a = True)

    return top_descriptions