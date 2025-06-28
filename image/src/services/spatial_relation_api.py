import requests
import decimal

def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    else:
        return obj

def call_spatial_api(geojson, refer_geom_dict):
    """
    Call the spatial relation API to get the spatial relations between the target geometry and reference geometries.
    """
    
    print("execute spatial relation...")

    target_geom = geojson["features"][0]

    spatial_relations = [
        "equals", "disjoint", "touches", "contains", "covers",
        "intersects", "within", "crosses", "overlaps", "azimuth"
    ]
    api_prefix = "https://getroadmile.sgis.tw/spatial-operation/"
    results = []

    for table_name, refer_geoms in refer_geom_dict.items():   
        # print("table_name: ", table_name)
        for feature in refer_geoms:
            for relation in spatial_relations:
                url = api_prefix + relation
                data = {
                    "targetGeom": target_geom,
                    "referGeom": feature
                }
                result = {}

                try:
                    response = requests.post(url, json=convert_decimal(data))
                    response.raise_for_status()
                    result = response.json()

                    if result['geojson']['type'] == 'FeatureCollection':
                        result['result'] = result['geojson']['features'][0]['properties'].get('NAME', "undefined")
                    else:
                        result['result'] = result['geojson']['properties'].get('NAME', "undefined")

                    result["ontology_class"] = table_name
                    # print("result: ", result)
                    results.append(result)
                except requests.RequestException as e:
                    print(f"Error in {relation} for {table_name}: {e}") 

    return results
