import time
from flask import jsonify
from owlready2 import Thing, get_ontology
import pandas as pd
from services.ontology.reasoning_api import run_reasoning 

def safe_name(x):
    return getattr(x, 'name', str(x))

def normalize_name(name):
    return str(name).replace("+", "_").replace(" ", "_")

def RunSemanticReasoning(sr_object, context, ontology_path='./ontology/LocationDescription.rdf'):
    """
    Initialize the ontology and map the spatial relations to the ontology.
    """

    # Load the ontology
    onto = {}
    timestamp = str(time.time()).replace(".", "_")
    onto[timestamp] = get_ontology(ontology_path).load()
    class_lookup = {cls.name: cls for cls in onto[timestamp].classes()}

    # Define the connection between the classes and Thing
    with onto[timestamp]:
        class BaseThing(Thing): pass
        class Particular(BaseThing): pass
        class PlaceName(BaseThing): pass
        class Localiser(BaseThing): pass
        class SpatialPreposition(BaseThing): pass
        class SpatialObjectType(BaseThing): pass

    # Assign classes and instances from spatial opeartions
    figure_feature_class = onto[timestamp]['FigureFeature']
    figure_feature_instance = figure_feature_class('targetFeature')

    context_class = onto[timestamp][context]
    context_instance = context_class('context'+str(context))

    for sr_item in sr_object:
        spatial_relation = sr_item.get('relation')
        refer_object_classname = sr_item.get('ontology_class')
        refer_object_name = sr_item.get('result')
        geojson_data = sr_item.get('geojson')
        other_info = sr_item.get('other_info')
        
        clean_name = normalize_name(refer_object_name)
        
        feature_class = onto[timestamp]["Feature"]
        if refer_object_classname not in class_lookup:
            print(f"❌ 本體中找不到類別：{refer_object_classname}")
            continue
        feature_typology_class = class_lookup[refer_object_classname]
        feature_toponym_class = onto[timestamp]["Toponym"]

        spatial_relation_class = onto[timestamp][spatial_relation]
        
        feature_instance = feature_class('referFeature'+clean_name)
        feature_typology_instance = feature_typology_class(clean_name+"_Typology_"+str(refer_object_classname))
        feature_typology_instance.qualityValue.append(str(refer_object_classname))
        feature_toponym_instance = feature_toponym_class(clean_name)
        spatial_relation_instance = spatial_relation_class(str(spatial_relation)+"_"+clean_name)

        feature_instance.hasQuality.append(feature_toponym_instance)
        feature_instance.hasQuality.append(feature_typology_instance)
        
        # Add Other Info (e.g. distance, direction) to Quality
        if other_info:
            print(f"Other info: {other_info} - {refer_object_name}")
            if spatial_relation == "AbsoluteDirection":
                if isinstance(other_info, list):
                    for direction in other_info:
                        spatial_relation_instance.directionValue.append(str(direction))
                else:
                    spatial_relation_instance.directionValue.append(str(other_info))

        # Add Geometry type to Quality
        geometry_type = None
        if geojson_data:
            geom = geojson_data.get("geometry")
            if not geom and geojson_data.get("type") == "Feature":
                geom = geojson_data.get("geometry")
            elif geojson_data.get("type") == "FeatureCollection":
                features = geojson_data.get("features", [])
                if features:
                    geom = features[0].get("geometry")

            if geom:
                g_type = geom.get("type")
                if g_type in {"Point", "LineString", "Polygon"}:
                    geometry_type = g_type
                elif g_type == "MultiPoint":
                    geometry_type = "MultiPoint"
                elif g_type == "MultiLineString":
                    geometry_type = "MultiLineString"
                elif g_type == "MultiPolygon":
                    geometry_type = "MultiPolygon"

        if geometry_type:
            print(f"Geometry type: {geometry_type} - {refer_object_name}")
            geometry_class = onto[timestamp].Geometry
            specific_geometry_class = onto[timestamp][geometry_type]
            if specific_geometry_class and issubclass(specific_geometry_class, geometry_class):
                geometry_instance = specific_geometry_class(f"referFeature{clean_name}_Geometry")
                geometry_instance.qualityValue.append(str(geometry_type))
                feature_instance.hasQuality.append(geometry_instance)
            else:
                geometry_instance = geometry_class(f"Geometry_{clean_name}")
                geometry_instance.qualityValue.append(str(geometry_type))
                feature_instance.hasQuality.append(geometry_instance)

        # Add RoadDirection to Quality
        action_class = onto[timestamp].Action
        if geojson_data:
            feature = geojson_data.get("features")[0]
            if feature:
                feature_property = feature.get("properties", {})
                road_direction = feature_property.get("Direction", None)
                if road_direction != None:
                    action_instance = action_class(f"referFeature{clean_name}_Action")
                    action_instance.qualityValue.append(str(road_direction))
                    feature_instance.hasQuality.append(action_instance)

        spatial_relation_instance.hasFeature.append(feature_instance)
        spatial_relation_instance.hasContext.append(context_instance)

    """
    Reasoning
    """
    onto_reasoned = {}
    onto_reasoned[timestamp] = run_reasoning(onto, timestamp)  # 執行推理


    """
    Extracting Full Results
    """
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
        localiser = []
        for loc_desc in location_descriptions:
            place_names = getattr(loc_desc, 'hasPlaceName', [])
            if place_names:
                place_name = safe_name(place_names[0])
            spatial_prepositions = getattr(loc_desc, 'hasSpatialPreposition', [])
            if spatial_prepositions:
                spatial_preposition = safe_name(spatial_prepositions[0])
            localisers = getattr(loc_desc, 'hasLocaliser', [])
            if localisers:
                localiser = [safe_name(loc) for loc in localisers]
            

        result_data.append({
            "Subject": subject_name,
            "PlaceName": place_name,
            "SpatialPreposition": spatial_preposition,
            "Localiser": localiser if localiser else None,
            "Qualities": qualities if qualities else None
        })

    # Clear the ontology
    onto[timestamp].destroy(update_relation = True, update_is_a = True)

    return result_data