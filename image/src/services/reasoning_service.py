from owlready2 import sync_reasoner, sync_reasoner_pellet, Imp
import json


def reasoning(onto, rule_path, infer_property_values=True, model="Pellet"):
    try:
        with open(rule_path, "r", encoding="utf-8") as f:
            rule_lines = [line.strip() for line in f if line.strip()]

        with onto:
            for idx, rule_text in enumerate(rule_lines):
                try:
                    rule = Imp()
                    rule.set_as_rule(rule_text)
                    # print(f"✅ Rule {idx + 1} OK: {rule_text}")
                except Exception as e:
                    print(f"❌ Rule {idx + 1} ERROR: {rule_text}")
                    # raise Exception(f"SWRL rule {idx + 1} failed: {rule_text}\n{str(e)}")

        with onto:
            if model == "Pellet":
                sync_reasoner_pellet(debug=True, infer_property_values=infer_property_values)
            else:
                sync_reasoner(debug=True, infer_property_values=infer_property_values)

        print("===========Reasoning END============")
        return onto
    except Exception as e:
        print("推論錯誤:" + rule_path, e)
        onto.destroy(update_relation=True, update_is_a=True)
        raise Exception("Reasoning step 0 failed: " + str(e))

def run_reasoning(onto):
    onto_with_context = reasoning(onto, "./ontology/context.txt")
    onto_with_semantic = reasoning(onto_with_context, './ontology/gis_to_semantic.txt')
    print("===========映射語意推論結果============")
    for idx, indiv in enumerate(onto_with_semantic.SpatialRelationship.instances()):
        locad_indiv = onto_with_semantic.LocationDescription(f"locad_{idx}")
        indiv.symbolize.append(locad_indiv)
    print("===========給定Quality============")

    for gf in onto_with_semantic.GroundFeature.instances():
        quality_class = onto_with_semantic['Scale']
        quality_instance = quality_class("scale_" + gf.name)
        quality_instance.qualityValue= ["0", ""]
        gf.hasQuality.append(quality_instance)
    
    with open("./ontology/traffic.json", encoding="utf-8") as f:
        traffic_data = json.load(f)

    for type_quality, quality_dict in traffic_data.items():
        for quality_class_name, quality_value in quality_dict.items():
            quality_class = onto_with_semantic[quality_class_name]
            if quality_class not in onto_with_semantic.classes():
                print(f"❌ 本體中找不到類別：{quality_class_name}")
                continue

            for gf in onto_with_semantic.GroundFeature.instances():
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

    print("===========給定Quality END============")
    print("===========映射結果輸出============")
    for gf in onto_with_semantic.GroundFeature.instances():
        for q in gf.hasQuality:
            print(f"[GroundFeature] {gf.name}")
            print(f"  ↳ hasQuality → [{q}] {q.name}")
            if hasattr(q, "qualityValue"):
                print(f"    ↳ qualityValue: {list(q.qualityValue)}")

    print("===========onto_with_word============")
    onto_with_word = reasoning(onto_with_semantic, './ontology/ehownet.txt')
                
    return onto_with_word
