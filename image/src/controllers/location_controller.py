from flask import Blueprint, jsonify, request
from services.db_service import fetch_data_from_db
from services.spatial_relation_api import call_spatial_api
from services.mapping_service import mapping_ontology
from utils.logger import log_error, log_info  
from utils.cleaner import clear_ontology  

location_bp = Blueprint("location", __name__)

@location_bp.route("/api/map_location", methods=["GET"])
def map_location():
    try:
        lon = float(request.args.get('lon'))
        lat = float(request.args.get('lat'))
        buffer_distance = float(request.args.get('buffer', 200))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    db_results = fetch_data_from_db(lon, lat, buffer_distance)
    sr_results = call_spatial_api(lon, lat, db_results)

    try:
        result = mapping_ontology(sr_results)
    except Exception as e:
        log_error(f"Error in mapping ontology: {str(e)}")  # 記錄錯誤

    # clear_ontology() 
    log_info("Mapping completed successfully")  # 記錄成功信息

    return {
        "spatial_relations": sr_results, 
        # "location_description": result
    }