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
        if refer_object_classname not in onto[timestamp]:
            raise ValueError(f"❌ 本體中找不到類別：{refer_object_classname}")
        feature_typology_class = onto[timestamp][refer_object_classname]
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
    onto_reasoned = run_reasoning(onto[timestamp])  # 執行推理

    # 產出資料
    print("=========end all reason===========")
    object_properties = [onto_reasoned.hasLocaliser, onto_reasoned.hasPlaceName, onto_reasoned.hasSpatialPreposition]
    
    data = []
    for prop in object_properties:
        for instance in prop.get_relations():
            try:
                subject, object_ = instance
                is_prefix = getattr(object_, 'isPrefix', None)
                data.append({
                    "Property": prop.name,
                    "Subject": safe_name(subject),
                    "Object": safe_name(object_),
                    "IsPrefix": is_prefix
                })
            except Exception as e:
                print(f"⚠️ Error processing relation {prop.name}: {e}")
                print(f"Instance content: {instance}")

    print("=========before groundby===========")
    print(data)


    result_data = []
    df = pd.DataFrame(data)
    df['Subject'] = df['Subject'].astype(str)
    grouped = df.groupby('Subject')

    print("=========grouped===========")
    print(grouped.groups)
    
    for subject, group in grouped: 
        place_name = group[group['Property'] == 'hasPlaceName']['Object'].values
        localisers = group[group['Property'] == 'hasLocaliser'][['Object', 'IsPrefix']].values
        spatial_prepositions = group[group['Property'] == 'hasSpatialPreposition']['Object'].values

        place_name = place_name[0] if place_name.size > 0 else None

        # 若沒有 localiser，仍需處理 spatial preposition
        if localisers.size == 0:
            if spatial_prepositions.size == 0:
                result_data.append({
                    "Subject": subject,
                    "PlaceName": place_name,
                    "Localiser": None,
                    "IsPrefix": None,
                    "SpatialPreposition": None
                })
            else:
                for spatial_preposition in spatial_prepositions:
                    result_data.append({
                        "Subject": subject,
                        "PlaceName": place_name,
                        "Localiser": None,
                        "IsPrefix": None,
                        "SpatialPreposition": spatial_preposition
                    })
        else:
            for localiser, is_prefix in localisers:
                spatial_set = spatial_prepositions if spatial_prepositions.size > 0 else [None]
                for spatial_preposition in spatial_set:
                    result_data.append({
                        "Subject": subject,
                        "PlaceName": place_name,
                        "Localiser": localiser,
                        "IsPrefix": is_prefix,
                        "SpatialPreposition": spatial_preposition
                    })

    print("=========Final Result===========")
    print(result_data)

    return result_data