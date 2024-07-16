# 輸入空間結果結合知識本體進行位置描述推論

## Introduction

This API allows the input of a dictionary of spatial relationships, where the key represents the spatial relationship, and the value represents the reference object type and name that have this spatial relationship with the input point. During the process, the spatial relationship results will be mapped to the ontology, and a two-stage reasoning process will be conducted. The first stage maps the spatial relationship to a semantic spatial relationship, and the second stage converts the semantic spatial relationship and the reference object name into natural language descriptions. Finally, one or more sets of location description texts will be outputted.

## Usage

You may pass the `json`(a dictionary of spatial relationships) as a POST parameter to access the API. 

```http
POST https://geospatialdescription.sgis.tw/api
```

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `json` | `json` | **Required**. A dictionary where the key is the spatial relationship, and the value is the type and name of the reference object having this relationship with the input point |

A JSON input may be like the following format:

```javascript
{
    "spatialrelation1": {
        "referObjectType1": ["objectName1", "objectName2"],
        "referObjectType2": ["objectName3", "objectName4"]
    },
    "spatialrelation2": {
        "referObjectType1": []
    }
}
```

## Responses

Return a JSON response in the following format:

```javascript
{
    "status": text,
    "data": {
        "SpatialOperation": dict,
        "Geometry": dict
    }
}
```

The `status` field indicates the status of the API, while the `data` field is subdivided into `SpatialOperation` which represents the results of spatial operations, and `Geometry` both recorded as dictionaries.

In the dictionary recorded under `SpatialOperation` the first level records spatial relationships, the second level records the reference spatial objects, and the third level records the objects that have spatial relationships with the input point. If empty, it indicates that there are no relevant spatial objects that have a spatial relationship with the input point.

Here is an example of one of the spatial relationships:

```javascript
"Intersect": {
    "Route": [],
    "RouteAncillaryFacilities": [],
    "County": [
        "臺北市"
    ]
}
```

Under the `Geometry` field, the first level records `totalFeatureCollection`, the second level records five spatial objects are recorded, including the input point, the road the input point maps to, another road the input point maps to, and the mileage marker points before and after the input point.

You can access the `totalFeatureCollection` field under `Geometry` to retrieve the GeoJSON of the five spatial objects. This API wraps them into a FeatureCollection geometry type.