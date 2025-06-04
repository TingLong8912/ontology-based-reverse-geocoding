import json

def addValueToQuality(refers, targets, onto_with_semantic, who_has_quality, dict_data):
    for target in targets:
        for class_name, class_content in dict_data.items():
            if who_has_quality == "SpatialPreposition" or who_has_quality == "Localiser":
                all_classes = [cls.name for parent in target.is_a for cls in [parent] + list(parent.ancestors())]
                if class_name in all_classes:
                    for quality_name, quality_value in class_content.items():
                        quality_class = onto_with_semantic[quality_name]
                        quality_instance = quality_class(target.name + "_" + quality_name)
                        for val in quality_value:
                            if val and (not hasattr(quality_instance, 'qualityValue') or val not in quality_instance.qualityValue):
                                quality_instance.qualityValue.append(val)
                        target.hasQuality.append(quality_instance)
            elif who_has_quality == "PlaceName":
                for place in refers.hasPlaceName:
                    quality_list = place.hasQuality
                    for quality in quality_list:
                        all_classes = [cls.name for parent in quality.is_a for cls in [parent] + list(parent.ancestors())]
                        if class_name in all_classes:
                            for quality_name, quality_value in class_content.items():
                                quality_class = onto_with_semantic[quality_name]
                                quality_instance = quality_class(place.name + "_" + quality_name)
                                for val in quality_value:
                                    if val and (not hasattr(quality_instance, 'qualityValue') or val not in quality_instance.qualityValue):
                                        quality_instance.qualityValue.append(val)
                                place.hasQuality.append(quality_instance)
            elif who_has_quality == "GroundFeature":
                quality_list = refers.hasQuality
                for quality in quality_list:
                    all_classes = [cls.name for parent in quality.is_a for cls in [parent] + list(parent.ancestors())]
                    if class_name in all_classes:
                        for quality_name, quality_value in class_content.items():
                            quality_class = onto_with_semantic[quality_name]
                            quality_instance = quality_class(refers.name + "_" + quality_name)
                            for val in quality_value:
                                if val and (not hasattr(quality_instance, 'qualityValue') or val not in quality_instance.qualityValue):
                                    quality_instance.qualityValue.append(val)
                            refers.hasQuality.append(quality_instance)

def assignQuality(onto_with_semantic, who_has_quality, data_path="./ontology/traffic.json"):
    """
    Assign Quality to SpatialPreposition or Localiser instances associated with LocationDescription,
    based on external data.
    """
    with open(data_path, encoding="utf-8") as f:
        dict_data = json.load(f)
    if who_has_quality in ["SpatialPreposition", "Localiser", "PlaceName"]:
        for locdesc in onto_with_semantic.LocationDescription.instances():
            if who_has_quality == "SpatialPreposition":
                targets = locdesc.hasSpatialPreposition
            elif who_has_quality == "Localiser":
                targets = locdesc.hasLocaliser
            elif who_has_quality == "PlaceName":
                targets = locdesc.hasPlaceName
            else:
                continue
            addValueToQuality(locdesc, targets, onto_with_semantic, who_has_quality, dict_data)
    else:
        for ground_feature in onto_with_semantic.GroundFeature.instances():
            addValueToQuality(ground_feature, onto_with_semantic.GroundFeature.instances(), onto_with_semantic, who_has_quality, dict_data)
     
    return onto_with_semantic
