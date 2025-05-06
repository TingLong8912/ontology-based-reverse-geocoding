from flask import Blueprint, jsonify, request, Response
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
        buffer_distance = float(request.args.get('buffer', 200))
        context = str(request.args.get('context', 'Traffic'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    if not (121.5 <= lon <= 122 and 25 <= lat <= 25.5):
        return jsonify({"error": "Location is outside the experimental map coverage."}), 400

    db_results = fetch_data_from_db(lon, lat, buffer_distance)
    sr_results = call_spatial_api(lon, lat, db_results)
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