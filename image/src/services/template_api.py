from owlready2 import Thing, get_ontology
import time
from itertools import product
from services.ontology.assign_quality_api import assignQuality
from services.template.to_fulltext import ToFullText
from services.template.formatLocation import format_locations, clean_za_prefix, remove_repeated_place_name
from services.template.calculate_quality import average_quality
from services.template.retrieveLocationInfo import retrieve_location_info

def template(locd_result, context,  w1, w2, ontology_path='./ontology/LocationDescription.rdf'):
    """
    This function is used to generate a template for the location description.
    It takes the location description and context as input and returns a template depending on the context.
    """

    """
    1. Ontology Mapping
    """
    # convert triplet to text
    full_text_list = ToFullText(locd_result)
    
    # Load the ontology
    onto = {}
    timestamp = str(time.time()).replace(".", "_")
    onto[timestamp] = get_ontology(ontology_path).load()

    # Define the connection between the classes and Thing
    with onto[timestamp]:
        class BaseThing(Thing): pass
        class Particular(BaseThing): pass
        class PlaceName(BaseThing): pass
        class Localiser(BaseThing): pass
        class SpatialPreposition(BaseThing): pass
        class SpatialObjectType(BaseThing): pass

    # Assign classes and instances from full_text
    print("===========映射位置描述文字結果============")
    for full_text in full_text_list:
        typology = full_text["type"]
        place_name = full_text.get("PlaceName", None)
        spatial_preposition_class_text = full_text.get("SpatialPrepositionClass", None)
        spatial_preposition = full_text.get("SpatialPreposition", None)
        localiser_class_text = full_text.get("LocaliserClass", None)
        localiser = full_text.get("Localiser", None)
        phrase = full_text["text"]
        qualitiesSR = full_text.get("QualitiesSR", None)

        locad_indiv = onto[timestamp].LocationDescription(str(phrase))
        typology_class = onto[timestamp][typology]
        typology_instance = typology_class(str(phrase) + "_Typology" + str(typology))
        typology_instance.qualityValue.append(str(typology))

        place_name_class = onto[timestamp].PlaceName
        if place_name:
            place_name_instance = place_name_class(str(phrase) + "_PlaceName" + str(place_name)) if place_name else None
            locad_indiv.hasPlaceName.append(place_name_instance)
            place_name_instance.hasQuality.append(typology_instance)

        spatial_preposition_class = onto[timestamp][spatial_preposition_class_text] if spatial_preposition_class_text else onto[timestamp].SpatialPreposition
        # Only create spatial_preposition_instance if spatial_preposition_class_text is not None or not empty
        if spatial_preposition_class_text:
            spatial_preposition_instance = spatial_preposition_class(str(phrase) + "_SpatialPreposition" + str(spatial_preposition))
            if qualitiesSR != None:
                for k, v in qualitiesSR.items():
                    qualitiesSR_class = onto[timestamp]["Prominence"] if qualitiesSR else None
                    qualitiesSR_class_instance = qualitiesSR_class(k)
                    qualitiesSR_class_instance.qualityValue.append(str(v))
                    spatial_preposition_instance.hasQuality.append(qualitiesSR_class_instance)
                    print("spatial_preposition_instance: ", spatial_preposition_instance)
                    print(f"Spatial Preposition Quality: {k} = {v}")  # Debugging line
            locad_indiv.hasSpatialPreposition.append(spatial_preposition_instance)

        localiser_class = onto[timestamp][localiser_class_text] if localiser_class_text else onto[timestamp].Localiser
        # Only create localiser_instance if localiser_class_text is not None or not empty
        if localiser_class_text:
            localiser_instance = localiser_class(str(phrase) + "_Localiser" + str(localiser))
            locad_indiv.hasLocaliser.append(localiser_instance)


    # Assign quality
    print("===========給定Quality============")
    onto[timestamp] = assignQuality(onto[timestamp], "PlaceName", data_path="./ontology/traffic.json")
    onto[timestamp] = assignQuality(onto[timestamp], "SpatialPreposition", data_path="./ontology/localiser.json")
    onto[timestamp] = assignQuality(onto[timestamp], "Localiser", data_path="./ontology/localiser.json")

    """
    2. Context Template
    """
    ###########################
    #
    # Traffic
    #
    ###########################
    if context == "Traffic":        
        loc_to_info = retrieve_location_info(onto[timestamp])

        township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        road_locs_without_admin = {loc: info['typologies'] for loc, info in loc_to_info.items() if ("NationalExpressway" in info["typologies"]) and "AtSpatialPreposition" in info["spatialPrepositions"] }
        road_locs_with_admin = [loc for loc, info in loc_to_info.items() if ("Road" in info["typologies"] and "NationalExpressway" not in info["typologies"]) and "AtSpatialPreposition" in info["spatialPrepositions"] ]
        road_near_locs = [loc for loc, info in loc_to_info.items() if "Road" in info['typologies']]
        landmark_locs = [loc for loc, info in loc_to_info.items() if "Landmark" in info["typologies"]]
        mileage_locs = {loc: info['typologies'] for loc, info in loc_to_info.items() if "RoadMileage" in info["typologies"]}
        
        landmark_locs = landmark_locs or [""]
        township_locs = township_locs or [""]

        # 開始組合
        combinations = {
            'combination': [],
            'avg_quality': []
        }

        if road_locs_without_admin:
            matched_mileages = []
            for r, r_classes in road_locs_without_admin.items():
                for m, m_classes in mileage_locs.items():
                    for m_class in m_classes:
                        m_class.replace("Mileage", "")
                        if m_class in r_classes:
                            matched_mileages.append(m)
                            break
                for m, l in product(matched_mileages, landmark_locs):
                    elements = [r, m, l]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "": 
                        combinations["combination"].append(f"{r}{m}")
                    else:
                        combinations["combination"].append(f"{r}{m}（{l}）")
        elif len(road_locs_with_admin)>0:
            for r in road_locs_with_admin:
                for t, l in product(township_locs, landmark_locs):
                    elements = [t, r, l]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "":
                        combinations["combination"].append(f"{t}{r}")
                    else:
                        combinations["combination"].append(f"{t}{r}（{l}）")
        else:
            qualities_to_check = ["Scale", "Prominence"]
            for r in road_near_locs:
                avg_qualities = average_quality(onto[timestamp], [r], qualities_to_check)
                combinations["combination"].append(r)
                combinations["avg_quality"].append(avg_qualities)

            for l in landmark_locs:
                avg_qualities = average_quality(onto[timestamp], [l], qualities_to_check)
                combinations["combination"].append(l)
                combinations["avg_quality"].append(avg_qualities)

            # 也請在這邊加上預設的行政區描述
            default_admin_locs = [township_locs[0] if township_locs else ""]
            qualities_to_check = ["Scale", "Prominence"]
            avg_qualities = average_quality(onto[timestamp], default_admin_locs, qualities_to_check)
            sentence = "".join(default_admin_locs)
            combinations["combination"].append(sentence)
            combinations["avg_quality"].append(avg_qualities)
            
        # 取得 top_n 的描述（依照平均 quality 值排序）
        top_n = 5  
        combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))

        combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
        top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    ###########################
    #
    # ReservoirDis
    #
    ###########################
    elif context == "ReservoirDis":
        loc_to_info = retrieve_location_info(onto[timestamp])
    
        combinations = {
            'combination': [],
            'avg_quality': []
        }
        rivers_locs = [loc for loc, info in loc_to_info.items() if "Stream" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
        rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverSource" in info["typologies"] ]
        rivers_locs += [loc for loc, info in loc_to_info.items() if "RiverMouth" in info["typologies"] ]
        reservoir_locs = [loc for loc, info in loc_to_info.items() if "Reservoir" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
        township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]

        townships_sentence = format_locations(township_locs, level='township')
        if len(reservoir_locs) == 0:
            for river in rivers_locs:        
                elements = township_locs + [river]
                qualities_to_check = ["Scale", "Prominence"]
                avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                sentence = f"{townships_sentence}{river}"
                print("sentence: ", sentence)
                combinations["avg_quality"].append(avg_qualities)
                combinations["combination"].append(sentence)
        else:
            for river in rivers_locs:
                for reservoir in reservoir_locs:
                    elements = township_locs + [river, reservoir]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    sentence = f"{townships_sentence}{river}({reservoir})"
                    print("sentence: ", sentence)
                    combinations["avg_quality"].append(avg_qualities)
                    combinations["combination"].append(sentence)
        
        top_n = 5  
        combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))
        combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
        top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    ###########################
    #
    # Thunderstorm
    #
    ###########################
    elif context == "Thunderstorm":
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

        print("elevation_locs: ", elevation_locs)
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
            print("river", rivers_locs)
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
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    ###########################
    #
    # Tsunami
    #
    ###########################
    elif context == "Tsunami":
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
        print("coastlines_out_locs: ", coastlines_out_locs)
        print("coastlines_part_locs: ", coastlines_part_locs)
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
                    print("sentence: ", sentence)
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
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    ###########################
    #
    # Earthquake
    #
    ###########################
    elif context == "EarthquakeEW":
        loc_to_info = retrieve_location_info(onto[timestamp])

        combinations = {
            'combination': [],
            'avg_quality': []
        }
        
        qualities_to_check = ["Scale", "Prominence"]
        out_localisers = {"OpenSeaLocaliser"}
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
        counties_locs = [loc for loc, info in loc_to_info.items() if "CountiesBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]
    
        print("counties_locs: ", counties_locs)
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
        if len(coastlines_part_locs) > 0:
            for part_coastline in coastlines_part_locs:
                elements = [part_coastline]
                avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                combinations["avg_quality"].append(avg_qualities)
                combinations["combination"].append(part_coastline)
        if len(coastlines_part_locs) > 0 and len(coastlines_out_locs) > 0:
            for part_coastline in coastlines_part_locs:
                for out_coastline in coastlines_out_locs:
                    elements = [part_coastline, out_coastline]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    sentence = f"{part_coastline}{out_coastline}"
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
        print("Top descriptions:", top_descriptions)
       
        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions