import psycopg2
import os
import json

DB_CONFIG = {
    "dbname": "gistl",
    "user": "TingLong",
    "password": "Acfg27354195",
    "host": "pdb.sgis.tw",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_data_from_db(lon, lat, buffer_distance):
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

    except psycopg2.Error as e:
        print(f"[DB ERROR] Unable to fetch table names: {e}")
    
    finally:
        cur.close()
        conn.close()

    return table_data