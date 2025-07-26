from services.template.calculate_quality import average_quality
from services.template.retrieveLocationInfo import retrieve_location_info
from services.template.formatLocation import clean_za_prefix, format_locations
from itertools import product

def generate_traffic_descriptions(onto, timestamp, w1, w2):
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
    # Clear the ontology
    onto[timestamp].destroy(update_relation = True, update_is_a = True)

    return top_descriptions