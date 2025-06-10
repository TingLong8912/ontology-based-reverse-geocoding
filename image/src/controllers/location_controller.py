from flask import Blueprint, jsonify, request, Response, stream_with_context
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
    """
    Map a location based on longitude, latitude, and context.
    This endpoint expects 'lon', 'lat', and 'context' as query parameters.
    """

    # Get longitude, latitude, and context from query parameters
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

    # Define the context to typologies mapping
    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)

    target_typologies = CONTEXT_TO_TYPOLOGIES.get(
        context,
        ['CountiesBoundary', 'TownshipsCititesDistrictsBoundary', 'VillagesBoundary']
    )

    # Determine buffer distance based on context
    if context == "Traffic":
        buffer_distance = 200
    elif context == "ReservoirDis" or context == "Thunderstorm":
        buffer_distance = 1000
    elif context == "Tsunami" or context == "EarthquakeEW":
        buffer_distance = 50000
    else:
        buffer_distance = 500

    # Get data from the database
    db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)

    # Call the spatial API to get spatial relations
    sr_results = call_spatial_api(geojson, db_results)
    for sr in sr_results:
        if sr.get('relation') == 'AbsoluteDirection':
            print(f"[DEBUG] AbsoluteDirection → bearing: {sr.get('bearing')}")
            print(f"[DEBUG] AbsoluteDirection → other_info: {sr.get('other_info')}")

    # Run semantic reasoning to get location description
    locad_result = RunSemanticReasoning(sr_results, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()
    log_info("Mapping completed successfully") 

    # Use the template function to generate multiLocad results
    multiLocad_results = template(locad_result, context)

    # Return the results as JSON
    return jsonify({
        "spatial_relations": sr_results,
        "location_description": locad_result,
        "multiLocad_results": multiLocad_results
    })


@location_bp.route("/api/stream_locd", methods=["GET", "POST"])
def stream_locd():
    def generate():
        try:
            raw_data = request.get_data(as_text=True)
            data = json.loads(raw_data)
            geojson = data.get("geojson")
            context = str(data.get("context"))
            yield f"data: {json.dumps({'stage': 'Request received', 'status': 'done'})}\n\n"

            features = geojson.get("features", [])
            if not features:
                yield f"data: {json.dumps({'stage': 'Validating geojson', 'status': 'error', 'message': 'No features found'})}\n\n"
                return
            geometry = features[0].get("geometry").get("type")

            data_path = "./ontology/context_to_typology.json"
            with open(data_path, encoding="utf-8") as f:
                CONTEXT_TO_TYPOLOGIES = json.load(f)
            target_typologies = CONTEXT_TO_TYPOLOGIES.get(context, ['CountiesBoundary', 'TownshipsCititesDistrictsBoundary', 'VillagesBoundary'])
            yield f"data: {json.dumps({'stage': 'Typology loaded', 'status': 'done'})}\n\n"

            if context == "Traffic":
                buffer_distance = 200
            elif context in ["ReservoirDis", "Thunderstorm"]:
                buffer_distance = 1000
            elif context in ["Tsunami", "EarthquakeEW"]:
                buffer_distance = 50000
            else:
                buffer_distance = 500
            yield f"data: {json.dumps({'stage': 'Buffer determined', 'status': 'done'})}\n\n"

            db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)
            yield f"data: {json.dumps({'stage': 'Database query', 'status': 'done'})}\n\n"

            sr_results = call_spatial_api(geojson, db_results)
            yield f"data: {json.dumps({'stage': 'Spatial relation reasoning', 'status': 'done', 'result': sr_results })}\n\n"

            locad_result = RunSemanticReasoning(sr_results, geometry, context)
            if hasattr(locad_result, "get_json"):
                locad_result = locad_result.get_json()
            yield f"data: {json.dumps({'stage': 'Semantic reasoning', 'status': 'done', 'result': locad_result })}\n\n"

            multiLocad_results = template(locad_result, context)
            yield f"data: {json.dumps({'stage': 'Template generation', 'status': 'done', 'result': multiLocad_results })}\n\n"

            result = {
                "spatial_relations": sr_results,
                "location_description": locad_result,
                "multiLocad_results": multiLocad_results
            }
            yield f"data: {json.dumps({'stage': 'Complete', 'status': 'done', 'result': result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'Error', 'status': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')