from services.template.calculate_quality import average_quality
from services.template.retrieveLocationInfo import retrieve_location_info
from services.template.formatLocation import clean_za_prefix, format_locations, keep_suffix_only_on_last

def generate_reservoir_descriptions(onto, timestamp, w1, w2):
    loc_to_info = retrieve_location_info(onto[timestamp])
    
    combinations = {
        'combination': [],
        'avg_quality': []
    }
    rivers_locs = [loc for loc, info in loc_to_info.items() if "Stream" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverSource" in info["typologies"] ]
    rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverMouth" in info["typologies"] ]
    reservoir_locs = [loc for loc, info in loc_to_info.items() if "Reservoir" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    reservoir_near_locs = [loc for loc, info in loc_to_info.items() if "Reservoir" in info["typologies"] and "AtSpatialPreposition" not in info["spatialPrepositions"] and "NearLocaliser" in info["localisers"]]
    township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]

    townships_sentence = format_locations(township_locs, level='township')
    if len(reservoir_locs) > 0:
        for river in rivers_locs:
            reservoir_locs_combinations =  "、".join(reservoir_locs)
            elements = township_locs + [river, reservoir_locs_combinations]
            qualities_to_check = ["Scale", "Prominence"]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            reservoirs = keep_suffix_only_on_last(reservoir_locs_combinations, "下游")
            sentence = f"{townships_sentence}{river}({reservoirs})"
            combinations["avg_quality"].append(avg_qualities)
            combinations["combination"].append(sentence)
    elif len(reservoir_near_locs) > 0:
        for reservoir in reservoir_near_locs:
            for river in rivers_locs:
                elements = township_locs + [reservoir, river]
                qualities_to_check = ["Scale", "Prominence"]
                avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                sentence = f"{townships_sentence}{river}({reservoir})"
                combinations["avg_quality"].append(avg_qualities)
                combinations["combination"].append(sentence)
    else:
        for river in rivers_locs:        
            elements = township_locs + [river]
            qualities_to_check = ["Scale", "Prominence"]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            sentence = f"{townships_sentence}{river}"
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