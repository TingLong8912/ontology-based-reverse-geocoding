from flask import Flask, jsonify, request
from owlready2 import Thing, get_ontology, sync_reasoner, Imp
import os
import pandas as pd
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

def get_class_hierarchy_json(ontology):
    def build_class_hierarchy(class_tree):
        class_info = {
            "class_name": class_tree.name,
            "instances": [individual.name for individual in class_tree.instances()],
            "subclasses": [build_class_hierarchy(subclass) for subclass in class_tree.subclasses()]
        }
        return class_info
    
    hierarchy = build_class_hierarchy(ontology.BaseThing)
    return hierarchy

@app.route('/api', methods=['POST'])
def api():
    # ///reload onto[timestamp]
    onto = {}
    input_data = request.json
    timestamp = str(time.time()).replace(".", "_")

    onto[timestamp] = get_ontology("./assets/simple_gsd.rdf").load()

    # 定義新的頂層類別 Thing
    with onto[timestamp]:
        class BaseThing(Thing):
            pass

    # 定義其他第一層類別，並將其與 Thing 連結
    with onto[timestamp]:
        class Particular(BaseThing):
            pass
        class PlaceName(BaseThing):
            pass
        class Localiser(BaseThing):
            pass
        class SpatialPreposition(BaseThing):
            pass
    
    # Set individuals
    ontology_classList = [
        'Equal', 'Intersect', 'Overlap', 'Cross',
        'Contain', 'Within', 'Touch',
        'BoundaryForCounty', 'DistanceNear', 'DistanceMiddle']
    ontology_dataPropList = [
        'DistanceForRoad', 'DirectionForRoad'
    ]

    SpatialOperation = input_data
    spatialOperationClassList = list(SpatialOperation.keys())
    input_feature_class = onto[timestamp]['GroundFeature']
    input_feature_instance = input_feature_class('inuptpoint')

    # Set class
    for spatial_relation in spatialOperationClassList:
        referObjects = SpatialOperation[spatial_relation]
        refObjectClassList = list(referObjects.keys())

        if spatial_relation in ontology_classList:
            # Get the class from the ontology
            spatial_relation_class = onto[timestamp][spatial_relation]

            for refObjectClass in refObjectClassList:
                placeFacet_class = onto[timestamp][refObjectClass]
                figure_feature_class = onto[timestamp]["FigureFeature"]

                individuals = referObjects[refObjectClass]

                for individual in individuals:
                    placeFacet_instance = placeFacet_class(str(individual))
                    figure_feature_instance = figure_feature_class(str(individual))

                    figure_feature_instance.hasQuality.append(placeFacet_instance)

                    # Create a new individual for the spatial relation class
                    individual_name = spatial_relation + str(individual)
                    spatial_relation_instance = spatial_relation_class(individual_name)

                    spatial_relation_instance.hasFigureFeature.append(figure_feature_instance)
                    spatial_relation_instance.hasGroundFeature.append(input_feature_instance)
        # Set data property
        elif spatial_relation in ontology_dataPropList:
            if spatial_relation == 'DistanceForRoad':
                spatial_relation_class = onto[timestamp]['DistanceRelation']
            elif spatial_relation == 'DirectionForRoad':
                spatial_relation_class = onto[timestamp]['DirectionRelation']

            for refObjectClass in refObjectClassList:
                placeFacet_class = onto[timestamp][refObjectClass]
                figure_feature_class = onto[timestamp]["FigureFeature"]

                individuals = referObjects[refObjectClass]
                for individual in individuals:
                    placeFacet_instance = placeFacet_class(individual)
                    figure_feature_instance = figure_feature_class(individual)

                    figure_feature_instance.hasQuality.append(placeFacet_instance)

                    # Create a new individual for the spatial relation class
                    individual_name = spatial_relation + "_" + str(individual)
                    spatial_relation_instance = spatial_relation_class(individual_name)

                    spatial_relation_instance.hasFigureFeature.append(figure_feature_instance)
                    spatial_relation_instance.hasGroundFeature.append(input_feature_instance)

                    if spatial_relation == 'DistanceForRoad':
                        spatial_relation_instance.DistanceForRoad.append(str(individual))
                    elif spatial_relation == 'DirectionForRoad':
                        spatial_relation_instance.DirectionForRoad.append(str(individual))
    
    # Set rules(gis to semantic)
    with onto[timestamp]:
        rule1 = Imp()
        rule1.set_as_rule("""
            Within(?relation), 
            FigureFeature(?referObject), Route(?referObject), hasFigureFeature(?relation, ?referObject),
            -> Upper(?relation)
        """)

        rule2 = Imp()
        rule2.set_as_rule("""
            Within(?relation), 
            FigureFeature(?referObject), Route(?referObject), hasFigureFeature(?relation, ?referObject),
            -> OnSite(?relation)
        """)

        rule3 = Imp()
        rule3.set_as_rule("""
            DistanceNear(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> Near(?relation)
        """)

        rule4 = Imp()
        rule4.set_as_rule("""
            DistanceMiddle(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> InBetween(?relation)
        """)

        rule5 = Imp()
        rule5.set_as_rule("""
            BoundaryForCounty(?relation), 
            FigureFeature(?referObject), County(?referObject), hasFigureFeature(?relation, ?referObject)
            -> Boundary(?relation)
        """)
        
        rule6 = Imp()
        rule6.set_as_rule("""
            DistanceRelation(?relation), DistanceForRoad(?relation, ?distance),
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> OnSite(?relation)
        """)

        rule7_1 = Imp()
        rule7_1.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "N")
            -> North(?relation)
        """)

        rule7_2 = Imp()
        rule7_2.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "S")
            -> South(?relation)
        """)

        rule7_3 = Imp()
        rule7_3.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "W")
            -> West(?relation)
        """)
        
        rule7_4 = Imp()
        rule7_4.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "E")
            -> East(?relation)
        """)

    # Reasoning 1
    with onto[timestamp]:
        sync_reasoner(infer_property_values = True)

    # 檢查推理結果並創建新的GeospatialDescription實例
    relation_classes = [onto[timestamp].Upper, onto[timestamp].OnSite, onto[timestamp].Near, onto[timestamp].InBetween, onto[timestamp].Boundary, onto[timestamp].North, onto[timestamp].South, onto[timestamp].West, onto[timestamp].East]

    for cls in relation_classes:
        for instance in cls.instances():
            if not onto[timestamp].search_one(is_a=onto[timestamp].GeospatialDescription, related_to=instance):
                new_description = onto[timestamp].GeospatialDescription(f"{instance.name}_description")
                instance.symbolize.append(new_description)

    # 設置規則
    with onto[timestamp]:
        rule_upper = Imp()
        rule_upper.set_as_rule("""
            Upper(?relation1), WordsOfUpper(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_near = Imp()
        rule_near.set_as_rule("""
            Near(?relation1), WordsOfNear(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_onSite = Imp()
        rule_onSite.set_as_rule("""
            OnSite(?relation1), WordsOfOnSite(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_boundary = Imp()
        rule_boundary.set_as_rule("""
            Boundary(?relation1), WordsOfBoundary(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), County(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_north = Imp()
        rule_north.set_as_rule("""
            North(?relation1), WordsOfNorth(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)
        
        rule_south = Imp()
        rule_south.set_as_rule("""
            South(?relation1), WordsOfSouth(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

        rule_west = Imp()
        rule_west.set_as_rule("""
            West(?relation1), WordsOfWest(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

        rule_east = Imp()
        rule_east.set_as_rule("""
            East(?relation1), WordsOfEast(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

    # 啟用推理機
    with onto[timestamp]:
        sync_reasoner(infer_property_values = True)

    object_properties = [onto[timestamp].hasLocaliser, onto[timestamp].hasPlaceName]
    data = []

    for prop in object_properties:
        for instance in prop.get_relations():
            subject, object_ = instance
            
            # 嘗試獲取 isPrefix 屬性值
            is_prefix = getattr(object_, 'isPrefix', None)  # 如果 object_ 沒有 isPrefix 屬性，將返回 None

            data.append({
                "Property": prop.name,
                "Subject": subject.name, # DistanceNear堤頂交流道_description
                "Object": object_.name,
                "IsPrefix": is_prefix
            })

    df = pd.DataFrame(data)

    result_data = []
    grouped = df.groupby('Subject')

    for subject, group in grouped:
        place_name = group[group['Property'] == 'hasPlaceName']['Object'].values
        localisers = group[group['Property'] == 'hasLocaliser']['Object'].values

        if place_name.size > 0:
            place_name = place_name[0]  # 假設每個 Subject 只有一個 hasPlaceName
        else:
            place_name = None

        for localiser in localisers:
            # 獲取當前 localiser 的 IsPrefix 值
            is_prefix = group[(group['Property'] == 'hasLocaliser') & (group['Object'] == localiser)]['IsPrefix'].values
            if is_prefix.size > 0:
                is_prefix = is_prefix[0]
            else:
                is_prefix = None

            result_data.append({
                "Subject": subject,
                "PlaceName": place_name,
                "Localiser": localiser,
                "IsPrefix": is_prefix
            })


    onto[timestamp].destroy(update_relation=True, update_is_a=True)
    return jsonify(result_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)