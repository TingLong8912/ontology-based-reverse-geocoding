from owlready2 import Thing, get_ontology
import time
from itertools import product
from services.ontology.assign_quality_api import assignQuality
import pandas as pd

def ToFullText(locd_result):
    """
    This function takes the location description json result and converts it into a full text format.
    """

    full_text = {}
    full_text_components = {}

    for entry in locd_result:
        qualities = entry.get("Qualities", {})
        typology = [k for k in qualities.keys() if "Typology" in k][0].split("_")[-1]

        if typology not in full_text:
            full_text[typology] = []
            full_text_components[typology] = []

        spatial_preposition = entry.get('SpatialPreposition', '')
        place_name = entry.get('PlaceName', '')
        localisers = entry.get('Localiser', [])

        if spatial_preposition == None:
            spatial_preposition = ''

        if localisers == None:
            localisers = ['']

        for localiser in localisers:
            full_text[typology].append(f"{spatial_preposition}{place_name}{localiser}")
            full_text_components[typology].append({
                "spatial_preposition": spatial_preposition or '',
                "place_name": place_name or '',
                "localiser": localiser or ''
            })

    for typology in full_text:
        full_text[typology] = list(set(full_text[typology]))
        # Remove duplicates in full_text_components accordingly
        seen = set()
        unique_components = []
        for comp in full_text_components[typology]:
            comp_tuple = (comp['spatial_preposition'], comp['place_name'], comp['localiser'])
            if comp_tuple not in seen:
                seen.add(comp_tuple)
                unique_components.append(comp)
        full_text_components[typology] = unique_components
        print("full_text_components[typology]:", full_text_components[typology])
    return full_text, full_text_components

def template(locd_result, context, ontology_path='./ontology/LocationDescription.rdf', target_typologies=None):
    """
    This function is used to generate a template for the location description.
    It takes the location description and context as input and returns a template depending on the context.
    """
    if context == "Traffic":
        full_text_dict, full_text_components = ToFullText(locd_result)
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
            components = full_text_components[typology]
            for idx, phrase in enumerate(phrases):
                comp = components[idx]
                locad_indiv = onto[timestamp].LocationDescription(str(phrase))
                typology_class = onto[timestamp][typology]
                typology_instance = typology_class(str(phrase) + "_Typology" + str(typology))
                typology_instance.qualityValue.append(str(typology))

                locad_indiv.hasQuality.append(typology_instance)
                
                if comp['spatial_preposition'] != '':
                    locad_indiv.hasSpatialPreposition = [onto[timestamp].SpatialPreposition(comp['spatial_preposition'])]
                if comp['place_name'] != '':
                    locad_indiv.hasPlaceName = [onto[timestamp].PlaceName(comp['place_name'])]
                if comp['localiser'] != '':
                    locad_indiv.hasLocaliser = [onto[timestamp].Localiser(comp['localiser'])]
    
        # Assign quality
        print("===========給定Quality============")
        onto[timestamp] = assignQuality(onto[timestamp], "LocationDescription")

        # 檢查映射結果
        print("===========映射結果輸出============")
        for gf in onto[timestamp].LocationDescription.instances():
            print(f"[LocationDescription] {gf.name}")
            for q in gf.hasQuality:
                print(f"  ↳ hasQuality → [{q}] {q.name}")
                if hasattr(q, "qualityValue"):
                    print(f"    ↳ qualityValue: {list(q.qualityValue)}")
            for q in gf.hasPlaceName:
                print(f"  ↳ hasPlaceName → [{q}] {q.name}")
            for q in gf.hasLocaliser:
                print(f"  ↳ hasLocaliser → [{q}] {q.name}")
            for q in gf.hasSpatialPreposition:
                print(f"  ↳ hasSpatialPreposition → [{q}] {q.name}")

        """
        Retrival
        """
        infer_typologies = ['Road', 'RoadMileage', 'Landmark', "BoundaryLine"]

        print("===========根據 typology 類別搜尋 LocationDescription ===========")
        typology_to_locs = {}

        for typology_name in infer_typologies:
            typology_class = onto[timestamp][typology_name]
            subclasses = list(typology_class.descendants()) 
            class_to_locs = {}
            for loc in onto[timestamp].LocationDescription.instances():
                for quality in loc.hasQuality:
                    cls = quality.__class__
                    if cls in subclasses:
                        cls_name = cls.name
                        if cls_name not in class_to_locs:
                            class_to_locs[cls_name] = []
                        class_to_locs[cls_name].append(
                            {
                                "name": loc.name,
                                "placeNames": [p.name for p in loc.hasPlaceName],
                                "spatialPrepositions": [sp.name for sp in loc.hasSpatialPreposition],
                                "localisers": [l.name for l in loc.hasLocaliser]
                            }
                        )
            if class_to_locs:
                typology_to_locs[typology_name] = class_to_locs

        print("===========地點描述資料檢查============")
        print(typology_to_locs)

        flattened_data = []
        for category, subtypes in typology_to_locs.items():
            for subtype, entries in subtypes.items():
                for entry in entries:
                    flattened_data.append({
                        "Category": category,
                        "Subtype": subtype,
                        "Name": entry["name"],
                        "PlaceNames": ", ".join(entry["placeNames"]),
                        "SpatialPrepositions": ", ".join(entry["spatialPrepositions"]),
                        "Localisers": ", ".join(entry["localisers"]),
                    })

        target_typologies = ['Road', 'RoadMileage', 'Landmark', "CountiesBoundary", "TownshipsCititesDistrictsBoundary"]         
       
        locad_df = pd.DataFrame(flattened_data)
        filtered_locad_df = locad_df[
            locad_df["Category"].isin(target_typologies) | locad_df["Subtype"].isin(target_typologies)
        ]
        filtered_locad_df = filtered_locad_df[
            (filtered_locad_df["SpatialPrepositions"].notna() & (filtered_locad_df["SpatialPrepositions"] != "")) |
            (filtered_locad_df["Localisers"].notna() & (filtered_locad_df["Localisers"] != ""))
        ]

        print("===========組合結果============")    
        df = filtered_locad_df.copy()

        df["CountiesBoundary"] = ""
        df["TownshipsCititesDistrictsBoundary"] = ""
        df["RoadMileage"] = ""
        df["Road"] = ""
        df["Landmark"] = ""

        # 映射分類邏輯
        for idx, row in df.iterrows():
            category = row["Category"]
            subtype = row["Subtype"]
            place_name = row["Name"]

            if category == "BoundaryLine":
                if "CountiesBoundary" in subtype:
                    df.at[idx, "CountiesBoundary"] = place_name
                elif "TownshipsCititesDistrictsBoundary" in subtype:
                    df.at[idx, "TownshipsCititesDistrictsBoundary"] = place_name
            elif category == "Road":
                df.at[idx, "Road"] = place_name
            elif category == "Landmark":
                df.at[idx, "Landmark"] = place_name
            elif category == "RoadMileage":
                df.at[idx, "RoadMileage"] = place_name
        
        results = []

        template_fields = [
            'CountiesBoundary',
            'TownshipsCititesDistrictsBoundary',
            'Road',
            'RoadMileage',
            'Landmark'
        ]

        field_values = {
            field: df[field][df[field] != ""].unique().tolist()
            for field in template_fields
        }

        # 取得所有組合（笛卡兒積）
        combinations = list(product(*field_values.values()))

        # 組合成描述句
        results = ["".join(parts) for parts in combinations]
       
        # Print the results
        print("===========組合結果============")
        for result in results:
            print(result)

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return results
    elif context == "Disaster":
        pass