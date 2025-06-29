from flask import Blueprint, jsonify, request, Response, stream_with_context
import json
from services.db_service import fetch_data_from_db
from services.spatial_relation_api import call_spatial_api
from services.semantic_reasoning_service import RunSemanticReasoning
from services.template_api import template
from utils.logger import log_error, log_info  
from utils.cleaner import clear_ontology  

location_bp = Blueprint("location", __name__)

@location_bp.route("/api/stream_locd", methods=["POST"])
def stream_locd():
    def generate():
        try:
            raw_data = request.get_data(as_text=True)
            data = json.loads(raw_data)
            geojson = data.get("geojson")
            context = str(data.get("context"))
            w1 = 0.6
            w2 = 0.4
            yield f"data: {json.dumps({'stage': 'Request received', 'status': 'done'})}\n\n"

            features = geojson.get("features", [])
            if not features:
                yield f"data: {json.dumps({'stage': 'Validating geojson', 'status': 'error', 'message': 'No features found'})}\n\n"
                return
            geometry = features[0].get("geometry").get("type")

            yield f"data: {json.dumps({'stage': 'Typology loaded', 'status': 'active'})}\n\n"
            data_path = "./ontology/context_to_typology.json"
            with open(data_path, encoding="utf-8") as f:
                CONTEXT_TO_TYPOLOGIES = json.load(f)
            default_typologies = ['CountiesBoundary']
            if context != "EarthquakeEW" and context != 'Tsunami':
                default_typologies.append('TownshipsCititesDistrictsBoundary')
                if geometry == "Point":
                    default_typologies.append('VillagesBoundary')
            target_typologies = CONTEXT_TO_TYPOLOGIES.get(context, []) + default_typologies
            yield f"data: {json.dumps({'stage': 'Typology loaded', 'status': 'done'})}\n\n"

            yield f"data: {json.dumps({'stage': 'Buffer determined', 'status': 'active'})}\n\n"
            if context == "Traffic":
                buffer_distance = 200
            elif context in ["ReservoirDis", "Thunderstorm"]:
                buffer_distance = 500
            elif context in ["Tsunami", "EarthquakeEW"]:
                buffer_distance = 50000
            else:
                buffer_distance = 500
            yield f"data: {json.dumps({'stage': 'Buffer determined', 'status': 'done'})}\n\n"

            yield f"data: {json.dumps({'stage': 'Database query', 'status': 'active'})}\n\n"
            db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)
            yield f"data: {json.dumps({'stage': 'Database query', 'status': 'done'})}\n\n"

            yield f"data: {json.dumps({'stage': 'Spatial relation reasoning', 'status': 'active'})}\n\n"
            sr_results = call_spatial_api(geojson, db_results)
            yield f"data: {json.dumps({'stage': 'Spatial relation reasoning', 'status': 'done', 'result': sr_results })}\n\n"

            yield f"data: {json.dumps({'stage': 'Semantic reasoning', 'status': 'active'})}\n\n"
            locad_result = RunSemanticReasoning(sr_results, geometry, context)
            if hasattr(locad_result, "get_json"):
                locad_result = locad_result.get_json()
            yield f"data: {json.dumps({'stage': 'Semantic reasoning', 'status': 'done', 'result': locad_result })}\n\n"

            yield f"data: {json.dumps({'stage': 'Template generation', 'status': 'active'})}\n\n"
            multiLocad_results = template(locad_result, context, w1, w2)
            yield f"data: {json.dumps({'stage': 'Template generation', 'status': 'done', 'result': multiLocad_results })}\n\n"

            yield f"data: {json.dumps({'stage': 'Complete', 'status': 'active'})}\n\n"
            result = {
                "spatial_relations": sr_results,
                "location_description": locad_result,
                "multiLocad_results": multiLocad_results
            }
            yield f"data: {json.dumps({'stage': 'Complete', 'status': 'done', 'result': result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'Error', 'status': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@location_bp.route("/api/get_locd_test", methods=["POST"])
def get_locd_test():
    # Get the geojson and context from the request body
    try:
        data = request.get_json()
        geojson = data.get("geojson")
        context = str(data.get("context"))
        features = geojson.get("features", [])
        w1 = float(data.get('w_one'))
        w2 = float(data.get('w_two'))

        if features:
            geometry = features[0].get("geometry").get("type")
        else:
            return jsonify({"error": "No features found in geojson"}), 400
        if not geojson or not context:
            return jsonify({"error": "Missing geometry or context"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid request: {e}"}), 400

    # Validate the context
    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)
    default_typologies = ['CountiesBoundary']
    if context != "EarthquakeEW" and context != 'Tsunami':
        default_typologies.append('TownshipsCititesDistrictsBoundary')
        if geometry == "Point":
            default_typologies.append('VillagesBoundary')
    target_typologies = CONTEXT_TO_TYPOLOGIES.get(context, []) + default_typologies

    if context == "Traffic":
        buffer_distance = 200
    elif context in ["ReservoirDis", "Thunderstorm"]:
        buffer_distance = 500
    elif context in ["Tsunami", "EarthquakeEW"]:
        buffer_distance = 50000
    else:
        buffer_distance = 500

    # Fetch data from the database
    db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)

    # Call the spatial API to get spatial relations
    sr_results = call_spatial_api(geojson, db_results)
    locad_result = RunSemanticReasoning(sr_results, geometry, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()

    # Use the template function to generate multiLocad results
    multiLocad_results = template(locad_result, context, w1, w2)

    # Return the results as JSON
    return jsonify({
        "spatial_relations": sr_results,
        "location_description": locad_result,
        "multiLocad_results": multiLocad_results
    })


@location_bp.route("/api/get_locd", methods=["POST"])
def get_locd():
    # Get the geojson and context from the request body
    try:
        data = request.get_json()
        geojson = data.get("geojson")
        context = str(data.get("context"))
        features = geojson.get("features", [])
        w1 = float(data.get('w_one'))
        w2 = float(data.get('w_two'))

        if features:
            geometry = features[0].get("geometry").get("type")
        else:
            return jsonify({"error": "No features found in geojson"}), 400
        if not geojson or not context:
            return jsonify({"error": "Missing geometry or context"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid request: {e}"}), 400

    # Validate the context
    data_path = "./ontology/context_to_typology.json"
    with open(data_path, encoding="utf-8") as f:
        CONTEXT_TO_TYPOLOGIES = json.load(f)
    default_typologies = ['CountiesBoundary']
    if context != "EarthquakeEW" and context != 'Tsunami':
        default_typologies.append('TownshipsCititesDistrictsBoundary')
        if geometry == "Point":
            default_typologies.append('VillagesBoundary')
    target_typologies = CONTEXT_TO_TYPOLOGIES.get(context, []) + default_typologies

    if context == "Traffic":
        buffer_distance = 200
    elif context in ["ReservoirDis", "Thunderstorm"]:
        buffer_distance = 500
    elif context in ["Tsunami", "EarthquakeEW"]:
        buffer_distance = 50000
    else:
        buffer_distance = 500

    # Fetch data from the database
    db_results = fetch_data_from_db(geojson, buffer_distance, target_typologies)

    # Call the spatial API to get spatial relations
    sr_results = call_spatial_api(geojson, db_results)
    locad_result = RunSemanticReasoning(sr_results, geometry, context)
    if hasattr(locad_result, "get_json"):
        locad_result = locad_result.get_json()

    # Use the template function to generate multiLocad results
    multiLocad_results = template(locad_result, context, w1, w2)

    # Return the results as JSON
    return jsonify({
        "data": multiLocad_results
    })
