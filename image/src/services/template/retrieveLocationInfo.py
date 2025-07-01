def retrieve_location_info(onto):
    """
    Retrieves combined typology and spatial preposition information for each LocationDescription.
    """
    loc_to_info = {}

    for loc in onto.LocationDescription.instances():
        loc_name = loc.name
        loc_to_info.setdefault(loc_name, {
            "typologies": [],
            "spatialPrepositions": [],
            "localisers": []
        })

        # typology: from hasPlaceName → hasQuality → class
        for placename in getattr(loc, "hasPlaceName", []):
            for quality in getattr(placename, "hasQuality", []):
                if getattr(quality, "is_a", None):
                    for cls in quality.is_a:
                        loc_to_info[loc_name]["typologies"].append(cls.name)
                        for super_cls in cls.ancestors():
                            if super_cls.name != "Thing":
                                loc_to_info[loc_name]["typologies"].append(super_cls.name)

        # spatial preposition: from hasSpatialPreposition → class and its ancestors
        for sp in getattr(loc, "hasSpatialPreposition", []):
            sp_class = sp.__class__
            loc_to_info[loc_name]["spatialPrepositions"].append(sp_class.name)
            for super_cls in sp_class.ancestors():
                if super_cls.name != "Thing":
                    loc_to_info[loc_name]["spatialPrepositions"].append(super_cls.name)
        
        # localisers: from hasLocaliser → class and its ancestors
        for sp in getattr(loc, "hasLocaliser", []):
            sp_class = sp.__class__
            loc_to_info[loc_name]["localisers"].append(sp_class.name)
            for super_cls in sp_class.ancestors():
                if super_cls.name != "Thing":
                    loc_to_info[loc_name]["localisers"].append(super_cls.name)

    return loc_to_info
