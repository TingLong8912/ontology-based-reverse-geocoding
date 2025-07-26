from owlready2 import Thing, get_ontology
import time
from services.ontology.assign_quality_api import assignQuality
from services.template.to_fulltext import ToFullText
from services.template.context_traffic import generate_traffic_descriptions
from services.template.context_reservoir import generate_reservoir_descriptions
from services.template.context_thunderstorm import generate_thunderstorm_descriptions
from services.template.context_tsunami import generate_tsunami_descriptions
from services.template.context_earthquake import generate_earthquake_descriptions

def template(locd_result, context,  w1, w2, ontology_path='./ontology/LocationDescription.rdf'):
    """
    This function is used to generate a template for the location description.
    It takes the location description and context as input and returns a template depending on the context.
    """

    """
    1. Ontology Mapping
    """
    # convert triplet to text
    full_text_list = ToFullText(locd_result)
    
    # Load the ontology
    onto = {}
    timestamp = str(time.time()).replace(".", "_")
    onto[timestamp] = get_ontology(ontology_path).load()

    # Define the connection between the classes and Thing
    with onto[timestamp]:
        class BaseThing(Thing): pass
        class Particular(BaseThing): pass
        class PlaceName(BaseThing): pass
        class Localiser(BaseThing): pass
        class SpatialPreposition(BaseThing): pass
        class SpatialObjectType(BaseThing): pass

    # Assign classes and instances from full_text
    for full_text in full_text_list:
        typology = full_text["type"]
        place_name = full_text.get("PlaceName", None)
        spatial_preposition_class_text = full_text.get("SpatialPrepositionClass", None)
        spatial_preposition = full_text.get("SpatialPreposition", None)
        localiser_class_text = full_text.get("LocaliserClass", None)
        localiser = full_text.get("Localiser", None)
        phrase = full_text["text"]
        qualitiesSR = full_text.get("QualitiesSR", None)

        locad_indiv = onto[timestamp].LocationDescription(str(phrase))
        typology_class = onto[timestamp][typology]
        typology_instance = typology_class(str(phrase) + "_Typology" + str(typology))
        typology_instance.qualityValue.append(str(typology))

        place_name_class = onto[timestamp].PlaceName
        if place_name:
            place_name_instance = place_name_class(str(phrase) + "_PlaceName" + str(place_name)) if place_name else None
            locad_indiv.hasPlaceName.append(place_name_instance)
            place_name_instance.hasQuality.append(typology_instance)

        spatial_preposition_class = onto[timestamp][spatial_preposition_class_text] if spatial_preposition_class_text else onto[timestamp].SpatialPreposition
        # Only create spatial_preposition_instance if spatial_preposition_class_text is not None or not empty
        if spatial_preposition_class_text:
            spatial_preposition_instance = spatial_preposition_class(str(phrase) + "_SpatialPreposition" + str(spatial_preposition))
            if qualitiesSR != None:
                for k, v in qualitiesSR.items():
                    qualitiesSR_class = onto[timestamp]["Prominence"] if qualitiesSR else None
                    qualitiesSR_class_instance = qualitiesSR_class(k)
                    qualitiesSR_class_instance.qualityValue.append(str(v))
                    spatial_preposition_instance.hasQuality.append(qualitiesSR_class_instance)
            locad_indiv.hasSpatialPreposition.append(spatial_preposition_instance)

        localiser_class = onto[timestamp][localiser_class_text] if localiser_class_text else onto[timestamp].Localiser
        # Only create localiser_instance if localiser_class_text is not None or not empty
        if localiser_class_text:
            localiser_instance = localiser_class(str(phrase) + "_Localiser" + str(localiser))
            locad_indiv.hasLocaliser.append(localiser_instance)


    # Assign quality
    onto[timestamp] = assignQuality(onto[timestamp], "PlaceName", data_path="./ontology/traffic.json")
    onto[timestamp] = assignQuality(onto[timestamp], "SpatialPreposition", data_path="./ontology/localiser.json")
    onto[timestamp] = assignQuality(onto[timestamp], "Localiser", data_path="./ontology/localiser.json")

    """
    2. Context Template
    """
    if context == "Traffic":        
        return generate_traffic_descriptions(onto, timestamp, w1, w2)
    elif context == "ReservoirDis":
        return generate_reservoir_descriptions(onto, timestamp, w1, w2)
    elif context == "Thunderstorm":
        return generate_thunderstorm_descriptions(onto, timestamp, w1, w2)
    elif context == "Tsunami":
        return generate_tsunami_descriptions(onto, timestamp, w1, w2)
    elif context == "EarthquakeEW":
        return generate_earthquake_descriptions(onto, timestamp, w1, w2)