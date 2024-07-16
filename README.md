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

The input JSON needs to be in the following format:

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

Here is an simple example of input:

```javascript
{
    "Within": {
        "County": ["Taipei"],
        "Route": ["National Highway No.1"]
    },
    "Intersect": {
        "County": ["Taipei"],
        "Route": ["National Highway No.1"],
        "RouteAncillaryFacilities": ["Daya System Interchange"]
    }
}
```

## Responses

The JSON response should be in the following format. Each element in the list will record three fields: `IsPrefix`, `Localiser`, and `PlaceName`. `IsPrefix` indicates whether the `Localiser` is placed as a prefix or suffix to the `PlaceName`. `Localiser` refers to the location descriptor, such as "上" (on) or "處" (at); `PlaceName` refers to the proper noun, such as "台北市" (Taipei City).

```javascript
[{'IsPrefix': [], 'Localiser': '', 'PlaceName': ''}, {'IsPrefix': [], 'Localiser': '', 'PlaceName': ''}, ...]
```

Here is an example of one of output:

```javascript
[
  {
    "IsPrefix": true,
    "Localiser": "上",
    "PlaceName": "Taipei"
  },
  {
    "IsPrefix": false,
    "Localiser": "處",
    "PlaceName": "National Highway No.1"
  }
]
```