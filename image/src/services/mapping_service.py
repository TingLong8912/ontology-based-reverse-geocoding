import time
from flask import jsonify
from owlready2 import Thing, get_ontology
import pandas as pd
from services.reasoning_service import run_reasoning 

def mapping_ontology(sr_object, ontology_path='./ontology/LocationDescription.rdf'):
    print("=========start mapping ontology===========")
    onto = {}
    timestamp = str(time.time()).replace(".", "_")
    onto[timestamp] = get_ontology(ontology_path).load()

    with onto[timestamp]:
        class BaseThing(Thing): pass
        class Particular(BaseThing): pass
        class PlaceName(BaseThing): pass
        class Localiser(BaseThing): pass
        class SpatialPreposition(BaseThing): pass
        class SpatialObjectType(BaseThing): pass

    ground_feature_class = onto[timestamp]['GroundFeature']
    ground_feature_instance = ground_feature_class('targetFeature')

    for sr_item in sr_object:
        spatial_relation = sr_item['relation']
        refer_object_classname = sr_item['ontology_class']
        refer_object_name = sr_item['result']

        print("refer_object_classname: ", refer_object_classname)
        figure_feature_class = onto[timestamp]["FigureFeature"]
        figure_feature_typology_class = onto[timestamp][refer_object_classname]
        figure_feature_toponym_class = onto[timestamp]["Toponym"]
        spatial_relation_class = onto[timestamp][spatial_relation]

        figure_feature_instance = figure_feature_class('referFeature')
        figure_feature_typology_instance = figure_feature_typology_class("referFeatureType")
        figure_feature_toponym_instance = figure_feature_toponym_class(refer_object_name)
        spatial_relation_instance = spatial_relation_class(str(spatial_relation)+"_"+str(refer_object_name))

        figure_feature_instance.hasQuality.append(figure_feature_typology_instance)
        figure_feature_instance.hasQuality.append(figure_feature_toponym_instance)
        spatial_relation_instance.hasFigureFeature.append(figure_feature_instance)
        spatial_relation_instance.hasGroundFeature.append(ground_feature_instance)

    print(list(onto[timestamp].classes()))

    # 呼叫推理服務
    onto = run_reasoning(onto, timestamp)  # 執行推理

    # 產出資料
    object_properties = [onto[timestamp].hasLocaliser, onto[timestamp].hasPlaceName]
    data = []
    for prop in object_properties:
        for instance in prop.get_relations():
            subject, object_ = instance
            is_prefix = getattr(object_, 'isPrefix', None)
            data.append({
                "Property": prop.name,
                "Subject": subject.name,
                "Object": object_.name,
                "IsPrefix": is_prefix
            })

    df = pd.DataFrame(data)
    result_data = []
    grouped = df.groupby('Subject')

    for subject, group in grouped:
        place_name = group[group['Property'] == 'hasPlaceName']['Object'].values
        localisers = group[group['Property'] == 'hasLocaliser']['Object'].values

        place_name = place_name[0] if place_name.size > 0 else None

        for localiser in localisers:
            is_prefix = group[(group['Property'] == 'hasLocaliser') & (group['Object'] == localiser)]['IsPrefix'].values
            is_prefix = is_prefix[0] if is_prefix.size > 0 else None

            result_data.append({
                "Subject": subject,
                "PlaceName": place_name,
                "Localiser": localiser,
                "IsPrefix": is_prefix
            })

    onto[timestamp].destroy(update_relation=True, update_is_a=True)
    return jsonify(result_data)