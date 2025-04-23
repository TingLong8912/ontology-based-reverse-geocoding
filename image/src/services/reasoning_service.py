from owlready2 import sync_reasoner_pellet, Imp

def reasoning(onto, rule_path, infer_property_values=True):
    try:
        with open(rule_path, "r", encoding="utf-8") as f:
            rule_lines = [line.strip() for line in f if line.strip()]

        with onto:
            for idx, rule_text in enumerate(rule_lines):
                rule = Imp()
                rule.set_as_rule(rule_text)
                print(f"Rule {idx + 1}: {rule_text}")

        with onto:
            sync_reasoner_pellet(debug=True, infer_property_values=infer_property_values)

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

    onto_with_word = reasoning(onto_with_semantic, './ontology/ehownet.txt', True)

    return onto_with_word
