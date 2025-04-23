from flask import Blueprint, jsonify, request, Response
import json
from services.db_service import fetch_data_from_db
from services.spatial_relation_api import call_spatial_api
from services.mapping_service import mapping_ontology
from utils.logger import log_error, log_info  
from utils.cleaner import clear_ontology  

location_bp = Blueprint("location", __name__)

@location_bp.route('/api/hello', methods=['GET'])
def hello():
    return "Hello, world!"

@location_bp.route("/api/map_location", methods=["GET"])
def map_location():
    try:
        lon = float(request.args.get('lon'))
        lat = float(request.args.get('lat'))
        buffer_distance = float(request.args.get('buffer', 200))
        context = str(request.args.get('context', 'Traffic'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    db_results = fetch_data_from_db(lon, lat, buffer_distance)
    sr_results = call_spatial_api(lon, lat, db_results)
    locad_result = mapping_ontology(sr_results, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()

    log_info("Mapping completed successfully")  # 記錄成功信息

    return jsonify({
        "spatial_relations": sr_results,
        "location_description": locad_result
    })