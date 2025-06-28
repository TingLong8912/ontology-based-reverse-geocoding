from owlready2 import Thing, get_ontology
import time
import json
from itertools import product
from services.ontology.assign_quality_api import assignQuality
from services.template.to_fulltext import ToFullText
from services.template.calculate_quality import get_quality_values, average_quality
import re

def format_locations(locations, level="township"):
    if not locations:
        return ""

    locations = [loc.replace("在", "") for loc in locations]

    if level == "township":
        prefix = locations[0][:3]
        main = locations[0]
        shortened = [loc.replace(prefix, "") if loc.startswith(prefix) else loc for loc in locations[1:]]
    elif level == "village":
        import re
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
    if sentence.startswith("在"):
        parts = sentence[1:].split("在")
        return "在" + "".join(parts)
    return sentence

def remove_repeated_place_name(text):
    return re.sub(r'(台灣|基隆市|新北市|臺北市)([^ ]*?)\1', r'\1\2', text)

def retrieve_location_info(onto):
    """
    Retrieves combined typology and spatial preposition information for each LocationDescription.
    """
    print("===========根據 typology + spatialPreposition 統一檢索 ===========")
    loc_to_info = {}

    for loc in onto.LocationDescription.instances():
        loc_name = loc.name
        loc_to_info.setdefault(loc_name, {
            "typologies": [],
            "spatialPrepositions": [],
            "localisers": []
        })

        # typology: from hasPlaceName → hasQuality → class
        for placename in getattr(loc, "hasPlaceName", []):
            for quality in getattr(placename, "hasQuality", []):
                if getattr(quality, "is_a", None):
                    for cls in quality.is_a:
                        loc_to_info[loc_name]["typologies"].append(cls.name)
                        for super_cls in cls.ancestors():
                            if super_cls.name != "Thing":
                                loc_to_info[loc_name]["typologies"].append(super_cls.name)

        # spatial preposition: from hasSpatialPreposition → class and its ancestors
        for sp in getattr(loc, "hasSpatialPreposition", []):
            sp_class = sp.__class__
            loc_to_info[loc_name]["spatialPrepositions"].append(sp_class.name)
            for super_cls in sp_class.ancestors():
                if super_cls.name != "Thing":
                    loc_to_info[loc_name]["spatialPrepositions"].append(super_cls.name)
        
        # localisers: from hasLocaliser → class and its ancestors
        for sp in getattr(loc, "hasLocaliser", []):
            sp_class = sp.__class__
            loc_to_info[loc_name]["localisers"].append(sp_class.name)
            for super_cls in sp_class.ancestors():
                if super_cls.name != "Thing":
                    loc_to_info[loc_name]["localisers"].append(super_cls.name)

    return loc_to_info

def template(locd_result, context,  w1, w2, ontology_path='./ontology/LocationDescription.rdf'):
    """
    This function is used to generate a template for the location description.
    It takes the location description and context as input and returns a template depending on the context.
    """

    """
    Ontology Mapping
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

    # 檢查映射結果
    print("===========映射結果輸出============")
    # for gf in onto[timestamp].LocationDescription.instances():
    #     print(f"[LocationDescription] {gf.name}")
    #     for q in gf.hasPlaceName:
    #         print(f"  ↳ hasPlaceName → [{q}] {q.name}")
    
    # for gf in onto[timestamp].PlaceName.instances():
    #     for q in gf.hasQuality:
    #         print(f"[PlaceName] {gf.name}")
    #         print(f"  ↳ hasQuality → [{q}] {q.name}")
    #         if hasattr(q, "qualityValue"):
    #             print(f"    ↳ qualityValue: {list(q.qualityValue)}")

    # for gf in onto[timestamp].Localiser.instances():
    #     for q in gf.hasQuality:
    #         print(f"[Localiser] {gf.name}")
    #         print(f"  ↳ hasQuality → [{q}] {q.name}")
    #         if hasattr(q, "qualityValue"):
    #             print(f"    ↳ qualityValue: {list(q.qualityValue)}")

    # for gf in onto[timestamp].SpatialPreposition.instances():
    #     for q in gf.hasQuality:
    #         print(f"[SpatialPreposition] {gf.name}")
    #         print(f"  ↳ hasQuality → [{q}] {q.name}")
    #         if hasattr(q, "qualityValue"):
    #             print(f"    ↳ qualityValue: {list(q.qualityValue)}")

    """
    Context Template
    """
    ###########################
    #
    # Traffic
    #
    ###########################
    if context == "Traffic":        
        loc_to_info = retrieve_location_info(onto[timestamp])

        print("loc_to_info: ", loc_to_info)
        county_locs = [loc for loc, info in loc_to_info.items() if "CountiesBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        village_locs = [loc for loc, info in loc_to_info.items() if "VillagesBoundary" in info["typologies"]  and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        road_within_locs = [loc for loc, info in loc_to_info.items() if "Road" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        road_near_locs = [loc for loc, info in loc_to_info.items() if "Road"]
        landmark_locs = [loc for loc, info in loc_to_info.items() if "Landmark" in info["typologies"]]

        # Step 1: 檢查哪些 road_locs 是 NationalExpressway 或 ProvincialHighway
        special_road_classes = [
            onto[timestamp].NationalExpressway,
            onto[timestamp].ProvincialHighway
        ]
        special_road_descendants = []
        for cls in special_road_classes:
            special_road_descendants += list(cls.descendants()) + [cls]

        road_locs_without_admin = []
        road_locs_with_admin = []
    
        for loc_name in road_within_locs:
            loc_indiv = onto[timestamp].LocationDescription(loc_name)
            is_special_road = False
            for q in loc_indiv.hasQuality:
                if q.is_a and any(cls in special_road_descendants for cls in q.is_a):
                    is_special_road = True
                    break
            if is_special_road:
                road_locs_without_admin.append(loc_name)
            else:
                road_locs_with_admin.append(loc_name)

        # 建立mileage為key的道路類別紀錄
        mileage_by_road = {}
        mileage_locs = [loc for loc, info in loc_to_info.items() if "Mileage" in info["typologies"]]
        for mileage_name in mileage_locs:
            if mileage_name == "":
                continue
            mileage_indiv = onto[timestamp].LocationDescription(mileage_name)
            for q in mileage_indiv.hasQuality:
                if q.is_a:
                    for cls in q.is_a:
                        road_type = cls.name.replace("Mileage", "")
                        mileage_by_road.setdefault(road_type, []).append(mileage_name)

        combinations = {
            'combination': [],
            'avg_quality': []
        }
        if len(road_within_locs):
            landmark_locs = landmark_locs or [""]
            print("===========組合道路、里程與地標描述============")
            # 不需要加上 Admin（特殊道路）
            for r in road_locs_without_admin:
                # Mileage <-> Road
                loc_indiv = onto[timestamp].LocationDescription(r)
                
                print("=============Mileage <-> Road=============")
                matched_mileages = []
                for quality in loc_indiv.hasQuality:
                    cls = quality.is_a[0]
                    super_classes = [ super_cls.name for super_cls in list(cls.ancestors())]
                    for key, item in mileage_by_road.items():
                        if key in super_classes:
                            matched_mileages+=item
                            break
                    break
             
                matched_mileages = matched_mileages or [""]

                for m, l in product(matched_mileages, landmark_locs):
                    elements = [r, m, l]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "": 
                        combinations["combination"].append(f"{r}{m}")
                    else:
                        combinations["combination"].append(f"{r}{m}（{l}）")
            print("===========組合道路、里程與地標描述（有 Admin）============")
            # 需要加上 Admin（一般道路）
            county_locs = county_locs or [""]
            township_locs = township_locs or [""]
            for r in road_locs_with_admin:
                loc_indiv = onto[timestamp].LocationDescription(r)
                for a, t, l in product(county_locs, township_locs, landmark_locs):
                    elements = [a, t, r, l]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "":
                        combinations["combination"].append(f"{a}{t}{r}")
                    else:
                        combinations["combination"].append(f"{a}{t}{r}（{l}）")
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
            default_admin_locs = [county_locs[0] if county_locs else "", township_locs[0] if township_locs else "", village_locs[0] if village_locs else ""]
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
        township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]

        townships_sentence = format_locations(township_locs, level='township')
        for river in rivers_locs:
            elements = township_locs + [river]
            qualities_to_check = ["Scale", "Prominence"]
            avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
            sentence = f"{townships_sentence}{river}"
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
        township_locs = [loc for loc, info in loc_to_info.items() if "TownshipsCititesDistrictsBoundary" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"] and not info['localisers']]
        elevation_locs = [loc for loc, info in loc_to_info.items() if "SpotElevation" in info["typologies"] and "AtSpatialPreposition" in info["spatialPrepositions"]]

        # Townships
        print("town")
        elements = township_locs
        qualities_to_check = ["Scale", "Prominence"]
        print(elements)
        avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check, w1, w2)
        sentence = format_locations(township_locs, level='township')
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
            print("coastlines_locs: ", coastlines_out_locs)
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