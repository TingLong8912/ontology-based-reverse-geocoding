import time
from flask import jsonify
from owlready2 import Thing, get_ontology
import pandas as pd
from services.reasoning_service import run_reasoning 

def safe_name(x):
    return getattr(x, 'name', str(x))

def mapping_ontology(sr_object, context, ontology_path='./ontology/LocationDescription.rdf'):
    print("=========start mapping ontology===========")
    onto = {}
    timestamp = str(time.time()).replace(".", "_")
    onto[timestamp] = get_ontology(ontology_path).load()
    class_lookup = {cls.name: cls for cls in onto[timestamp].classes()}

    with onto[timestamp]:
        class BaseThing(Thing): pass
        class Particular(BaseThing): pass
        class PlaceName(BaseThing): pass
        class Localiser(BaseThing): pass
        class SpatialPreposition(BaseThing): pass
        class SpatialObjectType(BaseThing): pass

    figure_feature_class = onto[timestamp]['FigureFeature']
    figure_feature_instance = figure_feature_class('targetFeature')

    context_class = onto[timestamp][context]
    context_instance = context_class('context'+str(context))


    for sr_item in sr_object:
        spatial_relation = sr_item['relation']
        refer_object_classname = sr_item['ontology_class']
        refer_object_name = sr_item['result']
        
        feature_class = onto[timestamp]["Feature"]
        if refer_object_classname not in class_lookup:
            print(f"❌ 本體中找不到類別：{refer_object_classname}")
            continue
        feature_typology_class = class_lookup[refer_object_classname]
        feature_toponym_class = onto[timestamp]["Toponym"]

        spatial_relation_class = onto[timestamp][spatial_relation]
        
        feature_instance = feature_class('referFeature'+str(refer_object_name))
        feature_typology_instance = feature_typology_class(str(refer_object_classname)+"_"+str(refer_object_name))
        feature_toponym_instance = feature_toponym_class(refer_object_name)
        spatial_relation_instance = spatial_relation_class(str(spatial_relation)+"_"+str(refer_object_name))

        feature_instance.hasQuality.append(feature_toponym_instance)
        feature_instance.hasQuality.append(feature_typology_instance)

        spatial_relation_instance.hasFeature.append(feature_instance)
        spatial_relation_instance.hasContext.append(context_instance)

    # 呼叫推理服務
    onto_reasoned = {}
    onto_reasoned[timestamp] = run_reasoning(onto[timestamp])  # 執行推理

    print("=========start extracting relationships===========")

    result_data = []
    spatial_relationship_class = onto_reasoned[timestamp].SpatialRelationship
    all_spatial_relationships = spatial_relationship_class.instances()

    for spatial_instance in all_spatial_relationships:
        subject_name = safe_name(spatial_instance)

        # SpatialRelationship -hasGroundFeature-> GroundFeature -hasQuality-> Quality
        ground_features = getattr(spatial_instance, 'hasGroundFeature', [])
        qualities = {}
        for ground_feature in ground_features:
            for quality in getattr(ground_feature, 'hasQuality', []):
                quality_value_list = getattr(quality, 'qualityValue', [])
                quality_value = quality_value_list[0] if quality_value_list else None
                qualities[safe_name(quality)] = quality_value

        # SpatialRelationship -symbolize-> LocationDescription -> hasPlaceName/SpatialPreposition/Localiser
        location_descriptions = getattr(spatial_instance, 'symbolize', [])
        place_name = None
        spatial_preposition = None
        localiser = None
        for loc_desc in location_descriptions:
            place_names = getattr(loc_desc, 'hasPlaceName', [])
            if place_names:
                place_name = safe_name(place_names[0])
            spatial_prepositions = getattr(loc_desc, 'hasSpatialPreposition', [])
            if spatial_prepositions:
                spatial_preposition = safe_name(spatial_prepositions[0])
            localisers = getattr(loc_desc, 'hasLocaliser', [])
            if localiser:
                localszer = safe_name(localisers[0])
            

        result_data.append({
            "Subject": subject_name,
            "PlaceName": place_name,
            "SpatialPreposition": spatial_preposition,
            "Localiser": localiser,
            "Qualities": qualities if qualities else None
        })

    print("=========Final Result===========")
    print(result_data)

    return result_data