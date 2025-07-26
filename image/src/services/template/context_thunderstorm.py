from services.template.calculate_quality import average_quality
from services.template.retrieveLocationInfo import retrieve_location_info
from services.template.formatLocation import clean_za_prefix, format_locations

def generate_thunderstorm_descriptions(onto, timestamp, w1, w2):
    loc_to_info = retrieve_location_info(onto[timestamp])

    combinations = {
        'combination': [],
        'avg_quality': []
    }
    rivers_locs = [loc for loc, info in loc_to_info.items() if "Stream" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverSource" in info["typologies"] ]
    rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverMouth" in info["typologies"] ]
    rivers_landmark_locs = [loc for loc, info in loc_to_info.items() if "Stream" in info["typologies"] and "NearLocaliser" in info["localisers"]]
    township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
    elevation_locs = [loc for loc, info in loc_to_info.items() if "SpotElevation" in info["typologies"]]

    rivers_landmark_locs = rivers_landmark_locs or [""]
    # Townships
    for l in rivers_landmark_locs:
        elements = township_locs + [l]
        qualities_to_check = ["Scale", "Prominence"]
        avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
        sentence = format_locations(township_locs, level='township') + f"({l})"
        combinations["avg_quality"].append(avg_qualities)
        combinations["combination"].append(sentence)
    
    # if elevatios
    if len(elevation_locs) > 0:
        for elevation in elevation_locs:
            elements = township_locs + [elevation]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            sentence = format_locations(township_locs, level='township') + f"({elevation})"
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(sentence)

    if len(rivers_locs) > 0:
        for river in rivers_locs:
            elements = township_locs + [river]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            sentence = format_locations(township_locs, level='township') + f"({river})"
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(sentence)

    top_n = 5  
    combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))
    combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
    top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]
    top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
    # Clear the ontology
    onto[timestamp].destroy(update_relation = True, update_is_a = True)

    return top_descriptions