from owlready2 import Thing, get_ontology
import time
from itertools import product
from services.ontology.assign_quality_api import assignQuality

def ToFullText(locd_result):
    """
    This function takes the location description json result and converts it into a full text format.
    """

    full_text = {}

    for entry in locd_result:
        qualities = entry.get("Qualities", {})
        typology = [k for k in qualities.keys() if "Typology" in k][0].split("_")[-1]

        if typology not in full_text:
            full_text[typology] = []

        spatial_preposition = entry.get('SpatialPreposition', '')
        place_name = entry.get('PlaceName', '')
        localisers = entry.get('Localiser', [])

        if spatial_preposition == None:
            spatial_preposition = ''

        if localisers == None:
            localiser = ''
            full_text[typology].append(f"{spatial_preposition}{place_name}{localiser}")
        else:
            for localiser in localisers:
                full_text[typology].append(f"{spatial_preposition}{place_name}{localiser}")

    for typology in full_text:
        full_text[typology] = list(set(full_text[typology]))

    return full_text

def template(locd_result, context, ontology_path='./ontology/LocationDescription.rdf', target_typologies=None):
    """
    This function is used to generate a template for the location description.
    It takes the location description and context as input and returns a template depending on the context.
    """
    if context == "Traffic":
        full_text_dict = ToFullText(locd_result)
        print(full_text_dict)

        """
        Ontology Mapping
        """
        # Load the ontology
        onto = {}
        timestamp = str(time.time()).replace(".", "_")
        onto[timestamp] = get_ontology(ontology_path).load()
        class_lookup = {cls.name: cls for cls in onto[timestamp].classes()}

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
        for typology, phrases in full_text_dict.items():
            for phrase in phrases:
                locad_indiv = onto[timestamp].LocationDescription(str(phrase))
                typology_class = onto[timestamp][typology]
                typology_instance = typology_class(str(phrase) + "_Typology" + str(typology))
                typology_instance.qualityValue.append(str(typology))

                locad_indiv.hasQuality.append(typology_instance)

        # Assign quality
        print("===========給定Quality============")
        onto[timestamp] = assignQuality(onto[timestamp], "LocationDescription")

        # 檢查映射結果
        print("===========映射結果輸出============")
        for gf in onto[timestamp].LocationDescription.instances():
            for q in gf.hasQuality:
                print(f"[LocationDescription] {gf.name}")
                print(f"  ↳ hasQuality → [{q}] {q.name}")
                if hasattr(q, "qualityValue"):
                    print(f"    ↳ qualityValue: {list(q.qualityValue)}")



        """
        Retrival
        """
        target_typologies = ['Road', 'RoadMileage', 'Landmark']

        print("===========根據 typology 類別搜尋 LocationDescription ===========")
        typology_to_locs = {}

        for typology_name in target_typologies:
            typology_class = onto[timestamp][typology_name]
            subclasses = list(typology_class.descendants()) 
            print(f"【{typology_name}】類別的子類別：", subclasses)
            matching_locs = []
            for loc in onto[timestamp].LocationDescription.instances():
                for quality in loc.hasQuality:
                    print(f"[DEBUG] {quality.name} 的 is_a：{quality.is_a}")
                    if quality.is_a and any(cls in subclasses for cls in quality.is_a):
                        matching_locs.append(loc.name)
                        break
            if matching_locs:
                typology_to_locs[typology_name] = matching_locs

        for typology, loc_names in typology_to_locs.items():
            print(f"【{typology}】類別下的地點描述：")
            for name in loc_names:
                print(f"  - {name}")
        
        # 組合 Road + RoadMileage + (Landmark)
        road_locs = typology_to_locs.get("Road", [])
        mileage_locs = typology_to_locs.get("RoadMileage", [])
        landmark_locs = typology_to_locs.get("Landmark", [])

        combinations = []
        if road_locs or landmark_locs:
            mileage_locs = mileage_locs or [""]
            road_locs = road_locs or [""]
            landmark_locs = landmark_locs or [""]
            for r, m, l in product(road_locs, mileage_locs, landmark_locs):
                combinations.append(f"{r}{m}（{l}）")

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return combinations
    elif context == "Disaster":
        pass