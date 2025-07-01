import psycopg2
import os
import json
from owlready2 import Thing, get_ontology
import time

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_data_from_db(geojson, buffer_distance, target_typologies):
    print("get db data...")

    schema_name = "LocaDescriber"
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Step 1: 取得 schema 下的所有表
    try:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """, (schema_name,))
        
        table_names = [row[0] for row in cur.fetchall()]  # 提取表名

        # Load the ontology
        onto = {}
        ontology_path='./ontology/LocationDescription.rdf'
        timestamp = str(time.time()).replace(".", "_")
        onto[timestamp] = get_ontology(ontology_path).load()
        with onto[timestamp]:
            class BaseThing(Thing): pass
            class Particular(BaseThing): pass
            class PlaceName(BaseThing): pass
            class Localiser(BaseThing): pass
            class SpatialPreposition(BaseThing): pass
            class SpatialObjectType(BaseThing): pass

        # subclasses
        subclasses = []
        for typology_name in target_typologies:
            typology_class = onto[timestamp][typology_name]
            subclasses += [cls.name for cls in typology_class.descendants()]
        subclasses = list(set(subclasses))
        
        table_names = [table for table in table_names if table in subclasses]
        
        # Step 2: 遍歷每個表，查詢相交的空間物件
        table_data = {}
        for table in table_names:
            try:
                query = f"""
                    SELECT id, ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geojson, * 
                    FROM "{schema_name}"."{table}" 
                    WHERE ST_Intersects(
                        geom,
                        ST_Buffer(
                            ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 3826),
                            %s
                        )
                    );
                """
                cur.execute(query, (json.dumps(geojson["features"][0]["geometry"]), buffer_distance))
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description] 

                geojson_features = []
                for row in rows:
                    row_dict = dict(zip(col_names, row))  
                    row_dict.pop("geom", None)  # 移除 geom 欄位
                    geojson_feature = {
                        "type": "Feature",
                        "geometry": json.loads(row_dict.pop("geojson")),  # 這裡的 geojson 現在是 EPSG:4326
                        "properties": row_dict  
                    }
                    geojson_features.append(geojson_feature)

                if geojson_features:
                    table_data[table] = geojson_features
            except psycopg2.Error as e:
                pass
                # print(f"Skipping table {table} due to error: {e}")

    except psycopg2.Error as e:
        print(f"[DB ERROR] Unable to fetch table names: {e}")
    
    finally:
        cur.close()
        conn.close()

    return table_data