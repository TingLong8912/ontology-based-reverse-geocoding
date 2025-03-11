from flask import Flask, jsonify, request
from owlready2 import Thing, get_ontology, sync_reasoner, Imp
import os
import pandas as pd
from flask_cors import CORS
import time
import json
import psycopg2
import requests

app = Flask(__name__)
CORS(app)

@app.route('/hello', methods=['GET'])
def hello():
    return "Hello, world!"

"""
NEW
"""
DB_CONFIG = {
    "dbname": "gistl",
    "user": "TingLong",
    "password": "Acfg27354195",
    "host": "pdb.sgis.tw",
    "port": "5432"
}

# Get Database Data by Buffer
### !!!!需要修改成不只點包含線或面
def getData(lon, lat, buffer_distance):
    print("get db data...")

    schema_name = "LocaDescriber"
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Step 1: 取得 schema 下的所有表
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """, (schema_name,))
    
    table_names = [row[0] for row in cur.fetchall()]  # 提取表名
    table_data = {}

    # Step 2: 遍歷每個表，查詢相交的空間物件
    for table in table_names:
        try:
            query = f"""
                SELECT id, ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geojson, * 
                FROM "{schema_name}"."{table}" 
                WHERE ST_Intersects(
                    geom,
                    ST_Buffer(
                        ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3826),
                        %s
                    )
                );
            """
            cur.execute(query, (lon, lat, buffer_distance))
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description] 

            geojson_features = []
            for row in rows:
                row_dict = dict(zip(col_names, row))  
                geojson_feature = {
                    "type": "Feature",
                    "geometry": json.loads(row_dict.pop("geojson")),  # 這裡的 geojson 現在是 EPSG:4326
                    "properties": row_dict  
                }
                geojson_features.append(geojson_feature)

            if geojson_features:
                table_data[table] = {
                    "type": "FeatureCollection",
                    "features": geojson_features
                }
        
        except psycopg2.Error as e:
            print(f"Skipping table {table} due to error: {e}")

    cur.close()
    conn.close()

    return table_data

def execSR(targetGeom, referGeomDict):
    print("execute spatial relation...")

    spatial_relations = [
        "equals", "disjoint", "touches", "contains", "covers",
        "intersects", "within", "crosses", "overlaps", "azimuth"
    ]
    api_prefix = "https://getroadmile.sgis.tw/spatial-operation/"
    
    results = []

    for table_name, referGeoms in referGeomDict.items():   
        for relation in spatial_relations:
            url = api_prefix + relation
            data = {
                "targetGeom": targetGeom,
                "referGeom": referGeoms
            }
            result = {}

            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                
                if result['geojson'] != []:
                    # for geom in result['geojson']:
                    #     if 'features' in geom:
                    #         geom["ontology_class"] = table_name
                    #         geom['result'] = geom['features'][0]['properties'].get('NAME', 'Unknown')
                    #     else:
                    #         geom["ontology_class"] = table_name
                    #         geom['result'] = geom['properties'].get('NAME', 'Unknown')
                            
                    results.append(result['geojson'])
            except requests.RequestException as e:
                print(f"Error in {relation} for {table_name}: {e}")

    return results

@app.route('/exec_onto', methods=['GET'])
def exec_onto():
    try:
        lon = float(request.args.get('lon'))
        lat = float(request.args.get('lat'))
        buffer_distance = float(request.args.get('buffer', 200))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    data = getData(lon, lat, buffer_distance)

    targetGeom = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "coordinates": [ lon, lat ],
            "type": "Point"
        }
    }

    sr_result = execSR(targetGeom, data)
  
    return jsonify(sr_result)

"""
OLD: Only For Road
"""
def get_class_hierarchy_json(ontology):
    def build_class_hierarchy(class_tree):
        class_info = {
            "class_name": class_tree.name,
            "instances": [individual.name for individual in class_tree.instances()],
            "subclasses": [build_class_hierarchy(subclass) for subclass in class_tree.subclasses()]
        }
        return class_info
    
    hierarchy = build_class_hierarchy(ontology.BaseThing)
    return hierarchy

@app.route('/api', methods=['POST'])
def api():
    # ///reload onto[timestamp]
    onto = {}
    input_data = request.json
    timestamp = str(time.time()).replace(".", "_")

    onto[timestamp] = get_ontology("./assets/simple_gsd.rdf").load()

    # 定義新的頂層類別 Thing
    with onto[timestamp]:
        class BaseThing(Thing):
            pass

    # 定義其他第一層類別，並將其與 Thing 連結
    with onto[timestamp]:
        class Particular(BaseThing):
            pass
        class PlaceName(BaseThing):
            pass
        class Localiser(BaseThing):
            pass
        class SpatialPreposition(BaseThing):
            pass
    
    # Set individuals
    ontology_classList = [
        'Equal', 'Intersect', 'Overlap', 'Cross',
        'Contain', 'Within', 'Touch',
        'BoundaryForCounty', 'DistanceNear', 'DistanceMiddle',
        'CrossForRoad', 'InFrontForRoad']
    ontology_dataPropList = [
        'DistanceForRoad', 'DirectionForRoad'
    ]

    SpatialOperation = input_data
    spatialOperationClassList = list(SpatialOperation.keys())
    input_feature_class = onto[timestamp]['GroundFeature']
    input_feature_instance = input_feature_class('inuptpoint')

    # Set class
    for spatial_relation in spatialOperationClassList:
        referObjects = SpatialOperation[spatial_relation]
        refObjectClassList = list(referObjects.keys())

        if spatial_relation in ontology_classList:
            # Get the class from the ontology
            spatial_relation_class = onto[timestamp][spatial_relation]

            for refObjectClass in refObjectClassList:
                placeFacet_class = onto[timestamp][refObjectClass]
                figure_feature_class = onto[timestamp]["FigureFeature"]

                individuals = referObjects[refObjectClass]

                for individual in individuals:
                    placeFacet_instance = placeFacet_class(str(individual))
                    figure_feature_instance = figure_feature_class(str(individual))

                    figure_feature_instance.hasQuality.append(placeFacet_instance)

                    # Create a new individual for the spatial relation class
                    individual_name = spatial_relation + "_" + str(individual)
                    spatial_relation_instance = spatial_relation_class(individual_name)

                    spatial_relation_instance.hasFigureFeature.append(figure_feature_instance)
                    spatial_relation_instance.hasGroundFeature.append(input_feature_instance)
        # Set data property
        elif spatial_relation in ontology_dataPropList:
            if spatial_relation == 'DistanceForRoad':
                spatial_relation_class = onto[timestamp]['DistanceRelation']
            elif spatial_relation == 'DirectionForRoad':
                spatial_relation_class = onto[timestamp]['DirectionRelation']

            for refObjectClass in refObjectClassList:
                placeFacet_class = onto[timestamp][refObjectClass]
                figure_feature_class = onto[timestamp]["FigureFeature"]

                individuals = referObjects[refObjectClass]
                for individual in individuals:
                    placeFacet_instance = placeFacet_class(individual)
                    figure_feature_instance = figure_feature_class(individual)

                    figure_feature_instance.hasQuality.append(placeFacet_instance)

                    # Create a new individual for the spatial relation class
                    individual_name = spatial_relation + "_" + str(individual)
                    spatial_relation_instance = spatial_relation_class(individual_name)

                    spatial_relation_instance.hasFigureFeature.append(figure_feature_instance)
                    spatial_relation_instance.hasGroundFeature.append(input_feature_instance)

                    if spatial_relation == 'DistanceForRoad':
                        spatial_relation_instance.DistanceForRoad.append(str(individual))
                    elif spatial_relation == 'DirectionForRoad':
                        spatial_relation_instance.DirectionForRoad.append(str(individual))
    
    # Set rules(gis to semantic)
    with onto[timestamp]:
        rule1 = Imp()
        rule1.set_as_rule("""
            Within(?relation), 
            FigureFeature(?referObject), Route(?referObject), hasFigureFeature(?relation, ?referObject),
            -> Upper(?relation)
        """)

        rule2 = Imp()
        rule2.set_as_rule("""
            Within(?relation), 
            FigureFeature(?referObject), Route(?referObject), hasFigureFeature(?relation, ?referObject),
            -> OnSite(?relation)
        """)

        rule3 = Imp()
        rule3.set_as_rule("""
            DistanceNear(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> Near(?relation)
        """)

        rule4 = Imp()
        rule4.set_as_rule("""
            DistanceMiddle(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> InBetween(?relation)
        """)

        rule5 = Imp()
        rule5.set_as_rule("""
            BoundaryForCounty(?relation), 
            FigureFeature(?referObject), County(?referObject), hasFigureFeature(?relation, ?referObject)
            -> Boundary(?relation)
        """)
        
        rule6 = Imp()
        rule6.set_as_rule("""
            DistanceRelation(?relation), DistanceForRoad(?relation, ?distance),
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> OnSite(?relation)
        """)

        rule7_1 = Imp()
        rule7_1.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "N")
            -> North(?relation)
        """)

        rule7_2 = Imp()
        rule7_2.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "S")
            -> South(?relation)
        """)

        rule7_3 = Imp()
        rule7_3.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "W")
            -> West(?relation)
        """)
        
        rule7_4 = Imp()
        rule7_4.set_as_rule("""
            DirectionRelation(?relation), DirectionForRoad(?relation, "E")
            -> East(?relation)
        """)

        rule8_1 = Imp()
        rule8_1.set_as_rule("""
            CrossForRoad(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> CrossC(?relation)
        """)

        rule8_2 = Imp()
        rule8_2.set_as_rule("""
            InFrontForRoad(?relation), 
            FigureFeature(?referObject), hasFigureFeature(?relation, ?referObject)
            -> InFrontC(?relation)
        """)

    # Reasoning 1
    with onto[timestamp]:
        sync_reasoner(infer_property_values = True)

    # 檢查推理結果並創建新的GeospatialDescription實例
    relation_classes = [
        onto[timestamp].Upper, onto[timestamp].OnSite, 
        onto[timestamp].Near, onto[timestamp].InBetween, 
        onto[timestamp].Boundary, onto[timestamp].North, 
        onto[timestamp].South, onto[timestamp].West, onto[timestamp].East,
        onto[timestamp].CrossC, onto[timestamp].InFrontC
    ]

    for cls in relation_classes:
        for instance in cls.instances():
            if not onto[timestamp].search_one(is_a=onto[timestamp].GeospatialDescription, related_to=instance):
                new_description = onto[timestamp].GeospatialDescription(f"{instance.name}_description")
                instance.symbolize.append(new_description)

    # 設置規則
    with onto[timestamp]:
        rule_upper = Imp()
        rule_upper.set_as_rule("""
            Upper(?relation1), WordsOfUpper(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_near = Imp()
        rule_near.set_as_rule("""
            Near(?relation1), WordsOfNear(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_onSite = Imp()
        rule_onSite.set_as_rule("""
            OnSite(?relation1), WordsOfOnSite(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_boundary = Imp()
        rule_boundary.set_as_rule("""
            Boundary(?relation1), WordsOfBoundary(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), County(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_north = Imp()
        rule_north.set_as_rule("""
            North(?relation1), WordsOfNorth(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)
        
        rule_south = Imp()
        rule_south.set_as_rule("""
            South(?relation1), WordsOfSouth(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

        rule_west = Imp()
        rule_west.set_as_rule("""
            West(?relation1), WordsOfWest(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

        rule_east = Imp()
        rule_east.set_as_rule("""
            East(?relation1), WordsOfEast(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word)
        """)

        rule_cross = Imp()
        rule_cross.set_as_rule("""
            CrossC(?relation1), WordsOfCrossForRoad(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

        rule_inFront = Imp()
        rule_inFront.set_as_rule("""
            InFrontC(?relation1), WordsOfInFrontForRoad(?word),
            GroundFeature(?inputpoint), hasGroundFeature(?relation1, ?inputpoint),
            FigureFeature(?referObject), hasFigureFeature(?relation1, ?referObject),
            GeospatialDescription(?description), symbolize(?relation1, ?description)
            -> hasLocaliser(?description, ?word), hasPlaceName(?description, ?referObject)
        """)

    # 啟用推理機
    with onto[timestamp]:
        sync_reasoner(infer_property_values = True)

    object_properties = [onto[timestamp].hasLocaliser, onto[timestamp].hasPlaceName]
    data = []

    for prop in object_properties:
        for instance in prop.get_relations():
            subject, object_ = instance
            
            # 嘗試獲取 isPrefix 屬性值
            is_prefix = getattr(object_, 'isPrefix', None)  # 如果 object_ 沒有 isPrefix 屬性，將返回 None

            data.append({
                "Property": prop.name,
                "Subject": subject.name, # DistanceNear堤頂交流道_description
                "Object": object_.name,
                "IsPrefix": is_prefix
            })

    df = pd.DataFrame(data)

    result_data = []
    grouped = df.groupby('Subject')

    for subject, group in grouped:
        place_name = group[group['Property'] == 'hasPlaceName']['Object'].values
        localisers = group[group['Property'] == 'hasLocaliser']['Object'].values

        if place_name.size > 0:
            place_name = place_name[0]  # 假設每個 Subject 只有一個 hasPlaceName
        else:
            place_name = None

        for localiser in localisers:
            # 獲取當前 localiser 的 IsPrefix 值
            is_prefix = group[(group['Property'] == 'hasLocaliser') & (group['Object'] == localiser)]['IsPrefix'].values
            if is_prefix.size > 0:
                is_prefix = is_prefix[0]
            else:
                is_prefix = None

            result_data.append({
                "Subject": subject,
                "PlaceName": place_name,
                "Localiser": localiser,
                "IsPrefix": is_prefix
            })


    onto[timestamp].destroy(update_relation=True, update_is_a=True)
    return jsonify(result_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)