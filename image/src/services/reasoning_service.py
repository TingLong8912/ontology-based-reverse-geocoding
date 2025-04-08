from owlready2 import sync_reasoner, Imp

def run_reasoning(onto, timestamp):
    try:
        # Step 1: 推論規則
        rule1 = Imp()
        rule1.set_as_rule("""
            Within(?relation), 
            FigureFeature(?referObject), hasQuality(?referObject, ?type), Road(?type),
            hasFigureFeature(?relation, ?referObject)
            -> Upper(?relation)
        """)

        with onto[timestamp]:
            sync_reasoner(debug=True)
        print("===========Reasoning(1) END============")
    except Exception as e:
        print("推論錯誤（Reasoning 1）:", e)
        onto[timestamp].destroy(update_relation=True, update_is_a=True)
        raise Exception("Reasoning step 1 failed: " + str(e))

    try:
        # Step 2: 推論規則
        rule_upper = Imp()
        rule_upper.set_as_rule("""
            Upper(?relation1), UpperLocalizer(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            LocationDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        with onto[timestamp]:
            sync_reasoner(infer_property_values=True)
    except Exception as e:
        print("推論錯誤（Reasoning 2）:", e)
        onto[timestamp].destroy(update_relation=True, update_is_a=True)
        raise Exception("Reasoning step 2 failed: " + str(e))

    return onto