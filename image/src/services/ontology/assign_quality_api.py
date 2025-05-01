import json

def assignQuality(onto_with_semantic, who_has_quality, data_path="./ontology/traffic.json"):
    """
    Assign Quality to GroundFeature instances based on the external data.
    """
    
    with open(data_path, encoding="utf-8") as f:
        traffic_data = json.load(f)

    for type_quality, quality_dict in traffic_data.items():
        for quality_class_name, quality_value in quality_dict.items():
            quality_class = onto_with_semantic[quality_class_name]
            if quality_class not in onto_with_semantic.classes():
                print(f"❌ 本體中找不到類別：{quality_class_name}")
                continue

            for gf in onto_with_semantic[who_has_quality].instances():
                for existing_quality in gf.hasQuality:
                    target_class = onto_with_semantic[type_quality]
                    if isinstance(existing_quality, target_class):
                        quality_instance = quality_class(gf.name + "_" + quality_class_name)
                        gf.hasQuality.append(quality_instance)
                        for val in quality_value:
                            if val and (not hasattr(quality_instance, 'qualityValue') or val not in quality_instance.qualityValue):
                                quality_instance.qualityValue.append(val)
                    else:
                        continue

    return onto_with_semantic