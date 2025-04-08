import requests

def call_spatial_api(lon, lat, refer_geom_dict):
    print("execute spatial relation...")

    target_geom = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "coordinates": [ lon, lat ],
            "type": "Point"
        }
    }

    spatial_relations = [
        "equals", "disjoint", "touches", "contains", "covers",
        "intersects", "within", "crosses", "overlaps", "azimuth"
    ]
    api_prefix = "https://getroadmile.sgis.tw/spatial-operation/"
    
    results = []

    for table_name, refer_geom in refer_geom_dict.items():   
        for relation in spatial_relations:
            url = api_prefix + relation
            data = {
                "targetGeom": target_geom,
                "referGeom": refer_geom
            }
            result = {}

            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
                result = response.json()

                if result['geojson']['type'] == 'FeatureCollection':
                    result['result'] = result['geojson']['features'][0]['properties'].get('NAME', "undefined")
                else:
                    result['result'] = result['geojson']['properties'].get('NAME', "undefined")

                result["ontology_class"] = table_name
                results.append(result)
            except requests.RequestException as e:
                print(f"Error in {relation} for {table_name}: {e}") 

    return results
