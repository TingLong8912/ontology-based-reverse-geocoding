def get_quality_values(onto, locad_indiv_name, target_quality: list):
    """
    取得某個 Typology 類別對應的所有 Quality 值。
    :param onto: 已載入的本體對象
    :param locad_indiv_name: 目標 LocationDescription 個體名稱
    :param target_quality: 欲檢索的 quality 類別名稱清單
    :return: {locad_indiv_name: {target_quality1: [], target_quality2: [], ...}}
    """
    result = {
        locad_indiv_name: {
            "PlaceName": {q: set() for q in target_quality},
            "SpatialPreposition": {q: set() for q in target_quality},
            "Localiser": {q: set() for q in target_quality}
        }
    }

    for loc in onto.LocationDescription.instances():
        if loc.name == locad_indiv_name:
            linked_entities = []

            # Collect linked PlaceName, SpatialPreposition, Localiser
            if hasattr(loc, "hasPlaceName"):
                linked_entities += loc.hasPlaceName
            if hasattr(loc, "hasSpatialPreposition"):
                linked_entities += loc.hasSpatialPreposition
            if hasattr(loc, "hasLocaliser"):
                linked_entities += loc.hasLocaliser

            for entity in linked_entities:
                for quality in getattr(entity, "hasQuality", []):
                    if hasattr(quality, "qualityValue"):
                        for cls in quality.is_a:
                            if cls.name in target_quality:
                                values = set(str(v) for v in quality.qualityValue)
                                if isinstance(entity, onto.PlaceName):
                                    result[locad_indiv_name]["PlaceName"][cls.name].update(values)
                                elif isinstance(entity, onto.SpatialPreposition):
                                    result[locad_indiv_name]["SpatialPreposition"][cls.name].update(values)
                                elif isinstance(entity, onto.Localiser):
                                    result[locad_indiv_name]["Localiser"][cls.name].update(values)
    # Convert sets back to lists for compatibility with downstream code
    for comp in ["PlaceName", "SpatialPreposition", "Localiser"]:
        for q in target_quality:
            result[locad_indiv_name][comp][q] = list(result[locad_indiv_name][comp][q])
    return result

def average_quality(onto, loc_names: list, qualities: list, w1 = 0.6, w2 = 0.4):
    """
    This function calculates the average quality values for a list of location names.
    """
    values = {q: [] for q in qualities}

    default_values = {
        "PlaceName": {
            "Scale": 1,         
            "Prominence": 0.0      
        }, 
        "SpatialPreposition": {
            "Scale": 0.25,         
            "Prominence": 0.0      
        }, 
        "Localiser": {
            "Scale": 0.25,         
            "Prominence": 0.0      
        }, 
    }

    # Insert scale_direction logic before score calculation
    scale_direction = {
        "PlaceName": "inverse", # 物件越明確(scale越小)越好
        "SpatialPreposition": "directional", # 越細緻(scale越大)越好
        "Localiser": "directional"
    }

    for name in loc_names:
        q_dict = get_quality_values(onto, name, qualities)[name]
        for component in ["PlaceName", "SpatialPreposition", "Localiser"]:
            for q in qualities:
                values_list = q_dict.get(component, {}).get(q, [])
                if not values_list:
                    val = float(default_values[component][q])
                    if q == "Scale" and scale_direction.get(component, "inverse") == "inverse":
                        val = 1 / val if val != 0 else 1
                    if q == "Scale":
                        val = val/20
                    values[q].append(val)
                    continue
                for v in values_list:
                    try:
                        val = float(v)
                        if q == "Scale" and scale_direction.get(component, "inverse") == "inverse":
                            val = 1 / val if val != 0 else 1
                        if q == "Scale":
                            val = val/20
                        values[q].append(val)
                    except ValueError:
                        continue
    
    scale_values = values.get("Scale", [])
    prominence_values = values.get("Prominence", [])
    
    scale_value = sum(scale_values) / len(scale_values) if scale_values else default_values["Scale"]
    prominence_value = sum(prominence_values) / len(prominence_values) if prominence_values else default_values["Prominence"]

    score = w1 * scale_value + w2 * prominence_value

    return {q: score}
