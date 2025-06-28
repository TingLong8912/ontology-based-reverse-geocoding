# LocaDescriber Ontology API

## Introduction

The LocaDescriber Ontology API provides semantic location descriptions based on spatial analysis results and knowledge-based ontology reasoning. By mapping spatial relations to an ontology, the system infers meaningful, natural language descriptions from structured spatial data.

## Features

- Accepts spatial relationships and reference object types as input.  
- Maps spatial relations to ontology-based semantic concepts.  
- Three-stage reasoning: ground feature depend on context, spatial-to-semantic mapping, and NL description generation.  
- Outputs structured natural language location descriptions.

## API Overview


**Endpoint**  
```
POST https://geospatialdescription.sgis.tw/api/get_locd
```
**Swagger UI:** [https://geospatialdescription.sgis.tw/apidocs/](https://geospatialdescription.sgis.tw/apidocs/)

**Content-Type:** `application/json`

## Input Format

The API expects a JSON object containing a GeoJSON FeatureCollection, a reasoning context, and optional weights for spatial and semantic reasoning.

### Example

```json
{
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [121.5, 25.0]
        }
      }
    ]
  },
  "context": "Traffic",
  "w_one": 0.6,
  "w_two": 0.4
}
```

## Response Format

The API returns an object with a `data` field that contains the location reasoning result.

### Example

```json
{
  "data": {}
}
```

## License

This project is part of a research initiative and is intended for academic and prototype use only.