from owlready2 import Thing, get_ontology
import time
import json
from itertools import product
from services.ontology.assign_quality_api import assignQuality
from services.template.to_fulltext import ToFullText
from services.template.calculate_quality import get_quality_values, average_quality

def clean_za_prefix(sentence):
    if sentence.startswith("在"):
        parts = sentence[1:].split("在")
        return "在" + "".join(parts)
    return sentence

def retrieve_typology_locations(onto, context):
    """
    This function is used to retrieve the description of target typology 
    """
    print("===========根據 typology 類別搜尋 LocationDescription ===========")

    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)
    target_typologies = CONTEXT_TO_TYPOLOGIES.get(
        context,
        ['CountiesBoundary', 'TownshipsCititesDistrictsBoundary', 'VillagesBoundary']
    )

    # print("目標 typology 類別:", target_typologies)
    typology_to_locs = {}
    for typology_name in target_typologies:
        typology_class = onto[typology_name]
        subclasses = list(typology_class.descendants()) 
        matching_locs = []
        for loc in onto.LocationDescription.instances():
            # print(f"Checking location: {loc.name}")
            for placename in loc.hasPlaceName: 
                # print(f"  - PlaceName: {placename.name}")
                for quality in placename.hasQuality:
                    # print(f"    ↳ Quality: {quality.name}, is_a: {quality.is_a}")
                    if quality.is_a and any(cls in subclasses for cls in quality.is_a):
                        print(f"Found matching location: {loc.name} for typology: {typology_name}")
                        matching_locs.append(loc.name)
                        break
        if matching_locs:
            typology_to_locs[typology_name] = matching_locs
    
    ############ for check ############
    # for typology, loc_names in typology_to_locs.items():
    #     print(f"【{typology}】類別下的地點描述：")
    #     for name in loc_names:
    #         print(f"  - {name}")
    ####################################

    return typology_to_locs

def template(locd_result, context, ontology_path='./ontology/LocationDescription.rdf'):
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
    print("full_text_list:", full_text_list)
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
    if context == "Traffic":        
        typology_to_locs = retrieve_typology_locations(onto[timestamp], context)

        # 組合 (Admin) + Road + RoadMileage + (Landmark)
        county_locs = list(set(typology_to_locs.get("CountiesBoundary", [])))
        township_locs = list(set(typology_to_locs.get("TownshipsCititesDistrictsBoundary", [])))
        road_locs = list(set(typology_to_locs.get("Road", [])))

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
    
        for loc_name in road_locs:
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
        mileage_locs = typology_to_locs.get("RoadMileage", [])
        for mileage_name in mileage_locs:
            if mileage_name == "":
                continue
            mileage_indiv = onto[timestamp].LocationDescription(mileage_name)
            for q in mileage_indiv.hasQuality:
                if q.is_a:
                    for cls in q.is_a:
                        road_type = cls.name.replace("Mileage", "")
                        mileage_by_road.setdefault(road_type, []).append(mileage_name)
        

        landmark_locs = list(set(typology_to_locs.get("Landmark", [])))
        
        combinations = {
            'combination': [],
            'avg_quality': []
        }
        if road_locs or landmark_locs:
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
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check)
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
                road_classes = [cls for q in loc_indiv.hasQuality for cls in (q.is_a or []) if cls not in special_road_descendants]
                for a, t, l in product(county_locs, township_locs, landmark_locs):
                    elements = [a, t, r, l]
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "":
                        combinations["combination"].append(f"{a}{t}{r}")
                    else:
                        combinations["combination"].append(f"{a}{t}{r}（{l}）")
        else:
            print("No road or landmark locations found.")
            # 需要處理
            
        # 取得 top_n 的描述（依照平均 quality 值排序）
        top_n = 5  
        combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))

        print("combined_with_quality:", combined_with_quality)

        combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
        top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    elif context == "ReservoirDis":
        typology_to_locs = retrieve_typology_locations(onto[timestamp], context)

        descriptions = []
        rivers = typology_to_locs.get("River", [])
        counties = typology_to_locs.get("CountiesBoundary", [""])
        townships = typology_to_locs.get("TownshipsCititesDistrictsBoundary", [""])
        villages = typology_to_locs.get("VillagesBoundary", [""])

        for river in rivers:
            for county in counties:
                for township in townships:
                    for village in villages:
                        elements = [county, township, village, river]
                        count_za = sum(1 for e in elements[1:] if "在" in e)
                        if count_za >= 1:
                            continue
                        sentence = f"{county}{township}{village}{river}"
                        descriptions.append(sentence)
        
        top_descriptions = descriptions[:5]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    elif context == "Thunderstorm":
        typology_to_locs = retrieve_typology_locations(onto[timestamp], context)

        descriptions = []
        counties = typology_to_locs.get("CountiesBoundary", [])
        townships = typology_to_locs.get("TownshipsCititesDistrictsBoundary", [])
        villages = typology_to_locs.get("VillagesBoundary", [])

        for county in counties:
            for township in townships:
                for village in villages:
                    elements = [county, township, village]
                    sentence = f"{county}{township}{village}"
                    descriptions.append(sentence)

        top_descriptions = descriptions[:5]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    elif context == "Tsunami":
        pass
    elif context == "EarthquakeEW":
        typology_to_locs = retrieve_typology_locations(onto[timestamp], context)

        descriptions = []
        coastlines = typology_to_locs.get("CoastLine", [])
        counties = typology_to_locs.get("CountiesBoundary", [])
        townships = typology_to_locs.get("TownshipsCititesDistrictsBoundary", [])
        villages = typology_to_locs.get("VillagesBoundary", [])

        # Hierarchical logic: check for each typology and combine accordingly
        if coastlines:
            for c in coastlines:
                descriptions.append(c)
        elif counties:
            for c in counties:
                descriptions.append(c)
        elif townships:
            for t in townships:
                for c in counties or [""]:
                    descriptions.append(f"{c}{t}")
        elif villages:
            for v in villages:
                for t in townships or [""]:
                    for c in counties or [""]:
                        descriptions.append(f"{c}{t}{v}")

        top_descriptions = descriptions[:5]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    else:
        typology_to_locs = retrieve_typology_locations(onto[timestamp], context)

        counties = typology_to_locs.get("CountiesBoundary", [""])
        townships = typology_to_locs.get("TownshipsCititesDistrictsBoundary", [""])
        villages = typology_to_locs.get("VillagesBoundary", [""])

        for county in counties:
            for township in townships:
                for village in villages:
                    elements = [county, township, village]
                    sentence = f"{county}{township}{village}"
                    descriptions.append(sentence)

        top_descriptions = descriptions[:5]
        top_descriptions = [clean_za_prefix(desc) for desc in top_descriptions]
        print("Top descriptions:", top_descriptions)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions