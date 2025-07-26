import time
from flask import jsonify
from owlready2 import Thing, get_ontology
import pandas as pd
from services.ontology.reasoning_api import run_reasoning 
from services.ontology.assign_quality_api import assignQuality

def safe_name(x):
    return getattr(x, 'name', str(x))

def normalize_name(name):
    return str(name).replace("+", "_").replace(" ", "_")

def RunSemanticReasoning(sr_object, geometry, context, ontology_path='./ontology/LocationDescription.rdf'):
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
    specific_geometry_class = onto[timestamp][geometry]
    geometry_instance = specific_geometry_class(f"targetFeature_Geometry")
    geometry_instance.qualityValue.append(str(geometry))
    figure_feature_instance.hasQuality.append(geometry_instance)

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
            if spatial_relation == "AbsoluteDirection":
                if isinstance(other_info, list):
                    for direction in other_info:
                        spatial_relation_instance.directionValue.append(str(direction))
                else:
                    spatial_relation_instance.directionValue.append(str(other_info))
            elif spatial_relation == "Intersects":
                if isinstance(other_info, list):
                    for area in other_info:
                        spatial_relation_instance.intersectArea.append(str(area))
                        typology_class = onto[timestamp]['Prominence']
                        typology_class_instance = typology_class(f"intersectArea_{clean_name}")  
                        typology_class_instance.qualityValue.append(str(area))

                        spatial_relation_instance.hasQuality.append(typology_class_instance)
                else:
                    spatial_relation_instance.intersectArea.append(str(other_info))
                    typology_class = onto[timestamp]['Prominence']
                    typology_class_instance = typology_class(f"intersectArea_{clean_name}")  
                    typology_class_instance.qualityValue.append(str(other_info))
                    spatial_relation_instance.hasQuality.append(typology_class_instance)

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
            road_direction = geojson_data.get("properties", {}).get("Direction", None)
            if road_direction != None:
                action_instance = action_class(f"referFeature{clean_name}_Action")
                action_instance.qualityValue.append(str(road_direction))
                feature_instance.hasQuality.append(action_instance)

        spatial_relation_instance.hasFeature.append(feature_instance)
        spatial_relation_instance.hasContext.append(context_instance)

    """
    Reasoning
    """

    # Assign Quality to PlaceName
    onto[timestamp] = assignQuality(onto[timestamp], "GroundFeature", data_path="./ontology/traffic.json")

    # Run reasoning on the ontology
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


        spatial_relation_qualities = getattr(spatial_instance, 'hasQuality', [])
        qualities_sr = {}
        for q in spatial_relation_qualities:
            quality_value_list_sr = getattr(q, 'qualityValue', [])
            quality_value_sr = quality_value_list_sr[0] if quality_value_list_sr else None
            qualities_sr[safe_name(q)] = quality_value_sr

        # SpatialRelationship -symbolize-> LocationDescription -> hasPlaceName/SpatialPreposition/Localiser
        location_descriptions = getattr(spatial_instance, 'symbolize', [])
        spatial_preposition = None
        localiser = []
        for loc_desc in location_descriptions:
            place_name_list = getattr(loc_desc, 'hasPlaceName', [])
            place_names = [safe_name(pn) for pn in place_name_list]
            spatial_prepositions = getattr(loc_desc, 'hasSpatialPreposition', [])
            spatial_preposition_class = None
            if spatial_prepositions:
                spatial_preposition_instance = spatial_prepositions[0]
                spatial_preposition = safe_name(spatial_preposition_instance)
                if spatial_preposition_instance.is_a:
                    spatial_preposition_class = spatial_preposition_instance.is_a[0].name
            localisers = getattr(loc_desc, 'hasLocaliser', [])
            localiser_class = None
            if localisers:
                localiser_instances = localisers
                localiser = [safe_name(loc) for loc in localiser_instances]
                localiser_class = []
                for loc in localiser_instances:
                    if loc.is_a:
                        localiser_class.append(loc.is_a[0].name)
                    else:
                        localiser_class.append(None)

        if isinstance(localiser, list) and isinstance(localiser_class, list) and len(localiser) == len(localiser_class):
            for loc, loc_class in zip(localiser, localiser_class):
                result_data.append({
                    "Subject": subject_name,
                    "PlaceName": place_names,
                    "SpatialPreposition": spatial_preposition,
                    "SpatialPrepositionClass": spatial_preposition_class,
                    "Localiser": loc,
                    "LocaliserClass": loc_class,
                    "Qualities": qualities if qualities else None,
                    "QualitiesSR": qualities_sr if qualities_sr else None
                })
        else:
            result_data.append({
                "Subject": subject_name,
                "PlaceName": place_names,
                "SpatialPreposition": spatial_preposition,
                "SpatialPrepositionClass": spatial_preposition_class,
                "Localiser": localiser if localiser else None,
                "LocaliserClass": localiser_class,
                "Qualities": qualities if qualities else None,
                "QualitiesSR": qualities_sr if qualities_sr else None
            })

    # Clear the ontology
    onto[timestamp].destroy(update_relation = True, update_is_a = True)

    return result_data