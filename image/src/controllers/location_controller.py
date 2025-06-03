from flask import Blueprint, jsonify, request
import json
from services.db_service import fetch_data_from_db
from services.spatial_relation_api import call_spatial_api
from services.semantic_reasoning_service import RunSemanticReasoning
from services.template_api import template
from utils.logger import log_error, log_info  
from utils.cleaner import clear_ontology  

location_bp = Blueprint("location", __name__)

@location_bp.route("/api/map_location", methods=["GET"])
def map_location():
    try:
        lon = float(request.args.get('lon'))
        lat = float(request.args.get('lat'))
        
        context = str(request.args.get('context'))
        print(f"[DEBUG] Received: lon={lon}, lat={lat}, context={context}")
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {}
                }
            ]
        }
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    if not (121.5 <= lon <= 122 and 25 <= lat <= 25.5):
        return jsonify({"error": "Location is outside the experimental map coverage."}), 400

    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)

    target_typologies = CONTEXT_TO_TYPOLOGIES.get(
        context,
        ['CountiesBoundary', 'TownshipsCititesDistrictsBoundary', 'VillagesBoundary']
    )

    if context == "Traffic":
        buffer_distance = 200
    elif context == "ReservoirDis" or context == "Thunderstorm":
        buffer_distance = 1000
    elif context == "Tsunami" or context == "EarthquakeEW":
        buffer_distance = 50000
    else:
        buffer_distance = 500

    db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)
    sr_results = call_spatial_api(geojson, db_results)
    for sr in sr_results:
        if sr.get('relation') == 'AbsoluteDirection':
            print(f"[DEBUG] AbsoluteDirection → bearing: {sr.get('bearing')}")
            print(f"[DEBUG] AbsoluteDirection → other_info: {sr.get('other_info')}")
    locad_result = RunSemanticReasoning(sr_results, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()

    log_info("Mapping completed successfully") 

    multiLocad_results = template(locad_result, context)

    return jsonify({
        "spatial_relations": sr_results,
        "location_description": locad_result,
        "multiLocad_results": multiLocad_results
    })


# New POST route for reverse geocoding using drawn geometry
@location_bp.route("/api/get_locd", methods=["POST"])
def get_locd():
    try:
        data = request.get_json()
        geojson = data.get("geojson")
        context = str(data.get("context"))
        features = geojson.get("features", [])
        if features:
            geometry = features[0].get("geometry").get("type")
        else:
            return jsonify({"error": "No features found in geojson"}), 400
        if not geojson or not context:
            return jsonify({"error": "Missing geometry or context"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid request: {e}"}), 400

    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)

    target_typologies = CONTEXT_TO_TYPOLOGIES.get(
        context,
        ['CountiesBoundary', 'TownshipsCititesDistrictsBoundary', 'VillagesBoundary']
    )

    if context == "Traffic":
        buffer_distance = 200
    elif context == "ReservoirDis" or context == "Thunderstorm":
        buffer_distance = 1000
    elif context == "Tsunami" or context == "EarthquakeEW":
        buffer_distance = 50000
    else:
        buffer_distance = 500

    db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)
    sr_results = call_spatial_api(geojson, db_results)
    locad_result = RunSemanticReasoning(sr_results, geometry, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()

    multiLocad_results = template(locad_result, context)

    return jsonify({
        "spatial_relations": sr_results,
        "location_description": locad_result,
        "multiLocad_results": multiLocad_results
    })