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


def get_quality_values(onto, locad_indiv_name, target_quality: list):
    """
    取得某個 Typology 類別對應的所有 Quality 值。
    :param onto: 已載入的本體對象
    :param locad_indiv_name: 目標 LocationDescription 個體名稱
    :param target_quality: 欲檢索的 quality 類別名稱清單
    :return: {locad_indiv_name: {target_quality1: [], target_quality2: [], ...}}
    """
    result = {locad_indiv_name: {q: [] for q in target_quality}}

    for loc in onto.LocationDescription.instances():
        if loc.name == locad_indiv_name:
            for quality in loc.hasQuality:
                if hasattr(quality, "qualityValue"):
                    for cls in quality.is_a:
                        if cls.name in target_quality:
                            values = [str(v) for v in quality.qualityValue]
                            result[locad_indiv_name][cls.name].extend(values)
    return result

def average_quality(onto, loc_names: list, qualities: list):
    """
    This function calculates the average quality values for a list of location names.
    """
    values = {q: [] for q in qualities}
    for name in loc_names:
        q_dict = get_quality_values(onto, name, qualities)[name]
        for q in qualities:
            values[q].extend([float(v) for v in q_dict[q] if v.replace('.', '', 1).isdigit()])
    print("執行平均結果：", loc_names, values)
    return {q: (sum(vals) / len(vals)) if vals else None for q, vals in values.items()}

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
        target_typologies = ['Road', 'RoadMileage', 'Landmark', 'CountiesBoundary', 'TownshipsCititesDistrictsBoundary']

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
        
        # 組合 (Admin) + Road + RoadMileage + (Landmark)
        county_locs = typology_to_locs.get("CountiesBoundary", [])
        township_locs = typology_to_locs.get("TownshipsCititesDistrictsBoundary", [])
        road_locs = typology_to_locs.get("Road", [])

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

        # 建立以道路類別為 key 的 mileage 對應
        mileage_by_road = {}

        mileage_locs = typology_to_locs.get("RoadMileage", [])
        for mileage_name in mileage_locs:
            if mileage_name == "":
                continue
            mileage_indiv = onto[timestamp].LocationDescription(mileage_name)
            for q in mileage_indiv.hasQuality:
                if q.is_a:
                    for cls in q.is_a:
                        mileage_by_road.setdefault(cls, []).append(mileage_name)

        landmark_locs = typology_to_locs.get("Landmark", [])

        combinations = {
            'combination': [],
            'avg_quality': []
        }
        if road_locs or landmark_locs:
            # 里程轉換
            all_mileage_names = [m for m in mileage_locs] or [""]
            converted_mileage_map = {}
            for m in all_mileage_names:
                if m == "":
                    converted_mileage_map[m] = ""
                elif "K_" in m:
                    try:
                        km, m_part = m.split("K_")
                        km_float = float(km) + float(m_part) / 1000
                        converted_mileage_map[m] = f"{km_float:.1f}公里"
                    except ValueError:
                        converted_mileage_map[m] = m
                else:
                    converted_mileage_map[m] = m
            landmark_locs = landmark_locs or [""]

            # 不需要加上 Admin（特殊道路）
            for r in road_locs_without_admin:
                loc_indiv = onto[timestamp].LocationDescription(r)
                road_classes = [cls for q in loc_indiv.hasQuality for cls in (q.is_a or []) if cls in special_road_descendants]
                matched_mileages = []
                for rc in road_classes:
                    matched_mileages += mileage_by_road.get(rc, [])
                matched_mileages = matched_mileages or [""]
                # 轉換里程
                matched_mileages = [converted_mileage_map.get(m, m) for m in matched_mileages]
                for m, l in product(matched_mileages, landmark_locs):
                    elements = [r, m, l]
                    count_za = sum(1 for e in elements[1:] if "在" in e)
                    if count_za >= 1:
                        continue
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "": 
                        combinations["combination"].append(f"{r}{m}")
                    else:
                        combinations["combination"].append(f"{r}{m}（{l}）")

            # 需要加上 Admin（一般道路）
            county_locs = county_locs or [""]
            township_locs = township_locs or [""]
            for r in road_locs_with_admin:
                loc_indiv = onto[timestamp].LocationDescription(r)
                road_classes = [cls for q in loc_indiv.hasQuality for cls in (q.is_a or []) if cls not in special_road_descendants]
                matched_mileages = []
                for rc in road_classes:
                    matched_mileages += mileage_by_road.get(rc, [])
                matched_mileages = matched_mileages or [""]
                matched_mileages = [converted_mileage_map.get(m, m) for m in matched_mileages]
                for a, t, m, l in product(county_locs, township_locs, matched_mileages, landmark_locs):
                    # 檢查是否含有多個 "在"，但只檢查 a 之後的元素
                    elements = [a, t, r, m, l]
                    count_za = sum(1 for e in elements[1:] if "在" in e)
                    if count_za >= 1:
                        continue
                    qualities_to_check = ["Scale", "Prominence"]
                    avg_qualities = average_quality(onto[timestamp], elements, qualities_to_check)
                    combinations["avg_quality"].append(avg_qualities)
                    if l == "":
                        combinations["combination"].append(f"{a}{t}{r}{m}")
                    else:
                        combinations["combination"].append(f"{a}{t}{r}{m}（{l}）")

        # 取得 top_n 的描述（依照平均 quality 值排序）
        top_n = 5  
        combined_with_quality = list(zip(combinations['combination'], combinations['avg_quality']))
        combined_with_quality.sort(key=lambda x: sum(v for v in x[1].values() if v is not None) / max(len([v for v in x[1].values() if v is not None]), 1), reverse=True)
        top_descriptions = [desc for desc, _ in combined_with_quality[:top_n]]

        # Clear the ontology
        onto[timestamp].destroy(update_relation = True, update_is_a = True)

        return top_descriptions
    elif context == "Disaster":
        pass