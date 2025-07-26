from owlready2 import sync_reasoner, sync_reasoner_pellet, Imp
import json
from services.ontology.assign_quality_api import assignQuality

def reasoning(onto, rule_path, infer_property_values=True, model="Pellet"):
    """
    Genearl Reasoning Function
    """

    try:
        # Read SWRL rules
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
        
        # Perform reasoning
        with onto:
            if model == "Pellet":
                sync_reasoner_pellet(debug=False, infer_property_values=infer_property_values)
            else:
                sync_reasoner(debug=False, infer_property_values=infer_property_values)

        return onto
    except Exception as e:
        onto.destroy(update_relation=True, update_is_a=True)
        raise Exception("Reasoning step 0 failed: " + str(e))

def run_reasoning(onto, timestamp):
    """
    The Main Framework of Three Stages Reasoning
    """

    onto_with_context = {}
    onto_with_semantic = {}
    onto_with_word = {}

    onto_with_context[timestamp] = reasoning(onto[timestamp], "./ontology/context.txt")
    onto_with_semantic[timestamp] = reasoning(onto_with_context[timestamp], './ontology/gis_to_semantic.txt')
    for idx, indiv in enumerate(onto_with_semantic[timestamp].SpatialRelationship.instances()):
        locad_indiv = onto_with_semantic[timestamp].LocationDescription(f"locad_{idx}")
        indiv.symbolize.append(locad_indiv)

    onto_with_semantic[timestamp] = assignQuality(onto_with_semantic[timestamp], "GroundFeature", data_path="./ontology/traffic.json")

    # 檢查映射結果
    # print("===========映射結果輸出============")
    # for gf in onto_with_semantic[timestamp].GroundFeature.instances():
    #     for q in gf.hasQuality:
    #         print(f"[GroundFeature] {gf.name}")
    #         print(f"  ↳ hasQuality → [{q}] {q.name}")
    #         if hasattr(q, "qualityValue"):
    #             print(f"    ↳ qualityValue: {list(q.qualityValue)}")

    onto_with_word[timestamp] = reasoning(onto_with_semantic[timestamp], './ontology/ehownet.txt')

    return onto_with_word[timestamp]
