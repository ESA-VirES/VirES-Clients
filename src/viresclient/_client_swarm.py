# pylint: disable=missing-docstring, invalid-name,line-too-long

import datetime
import json
import os
import sys
from collections import OrderedDict
from io import StringIO
from textwrap import dedent
from warnings import warn

from pandas import read_csv
from tqdm import tqdm

from ._client import TEMPLATE_FILES, ClientRequest, WPSInputs
from ._data import CONFIG_SWARM
from ._data_handling import ReturnedDataFile
from ._wps.environment import JINJA2_ENVIRONMENT
from ._wps.time_util import parse_datetime

TEMPLATE_FILES = {
    **TEMPLATE_FILES,
    "sync": "vires_fetch_filtered_data.xml",
    "async": "vires_fetch_filtered_data_async.xml",
    "model_info": "vires_get_model_info.xml",
    "times_from_orbits": "vires_times_from_orbits.xml",
    "get_observatories": "vires_get_observatories.xml",
    "get_conjunctions": "vires_get_conjunctions.xml",
    "get_collection_info": "vires_get_collection_info.xml",
}

REFERENCES = {
    "General Swarm": (
        " Swarm Data Handbook, https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook ",
        " The Swarm Satellite Constellation Application and Research Facility (SCARF) and Swarm data products, https://doi.org/10.5047/eps.2013.07.001 ",
        " Swarm Science Data Processing and Products (2013), https://link.springer.com/journal/40623/65/11/page/1 ",
        " Special issue “Swarm science results after 2 years in space (2016), https://www.springeropen.com/collections/swsr ",
        " Earth's Magnetic Field: Understanding Geomagnetic Sources from the Earth's Interior and its Environment (2017), https://link.springer.com/journal/11214/206/1/page/1 ",
    )
}

MODEL_REFERENCES = {
    "IGRF": (
        " International Geomagnetic Reference Field: the thirteenth generation, (https://doi.org/10.1186/s40623-020-01288-x) ",
        " https://www.ngdc.noaa.gov/IAGA/vmod/igrf.html ",
    ),
    "IGRF12": (
        " International Geomagnetic Reference Field: the 12th generation, https://doi.org/10.1186/s40623-015-0228-9 ",
        " https://www.ngdc.noaa.gov/IAGA/vmod/igrf.html "
        " deprecated model identifier, use IGRF instead",
    ),
    "CHAOS-Core": (
        "CHAOS-8 Core field (SH degrees 1-20)",
        " http://www.spacecenter.dk/files/magnetic-models/CHAOS-8/ ",
    ),
    "CHAOS-Static": (
        "CHAOS-8 crust field (SH degrees 21-185)",
        " http://www.spacecenter.dk/files/magnetic-models/CHAOS-8/ ",
    ),
    "CHAOS-MMA-Primary": (
        "CHAOS-8 Primary (external) magnetospheric field",
        " http://www.spacecenter.dk/files/magnetic-models/CHAOS-8/ ",
    ),
    "CHAOS-MMA-Secondary": (
        "CHAOS-8 Secondary (internal) magnetospheric field",
        " http://www.spacecenter.dk/files/magnetic-models/CHAOS-8/ ",
    ),
    "CHAOS-6-Core": (
        "CHAOS Core field",
        " deprecated model identifier, use CHAOS-Core instead",
    ),
    "CHAOS-6-Static": (
        "CHAOS crust field",
        " deprecated model identifier, use CHAOS-Static instead",
    ),
    "CHAOS-6-MMA-Primary": (
        "CHAOS Primary (external) magnetospheric field",
        " deprecated model identifier, use CHAOS-MMA-Primary instead",
    ),
    "CHAOS-6-MMA-Secondary": (
        "CHAOS-Secondary (internal) magnetospheric field",
        " deprecated model identifier, use CHAOS-MMA-Secondary instead",
    ),
    "MF7": (
        "MF7 crustal field model, derived from CHAMP satellite observations",
        " http://geomag.org/models/MF7.html",
    ),
    "LCS-1": (
        "The LCS-1 high-resolution lithospheric field model, derived from CHAMP and Swarm satellite observations",
        " http://www.spacecenter.dk/files/magnetic-models/LCS-1/",
    ),
    "MCO_SHA_2C": (
        "[Comprehensive Inversion]: Core field of CIY4",
        " A comprehensive model of Earth’s magnetic field determined from 4 years of Swarm satellite observations, https://doi.org/10.1186/s40623-018-0896-3 ",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MCO/SW_OPER_MCO_VAL_2C_20131201T000000_20180101T000000_0401.ZIP ",
    ),
    "MCO_SHA_2D": (
        "[Dedicated Chain]: Core field",
        "An algorithm for deriving core magnetic field models from the Swarm data set, https://doi.org/10.5047/eps.2013.07.005 ",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MCO/SW_OPER_MCO_VAL_2D_20131126T000000_20180101T000000_0401.ZIP ",
    ),
    "MLI_SHA_2C": (
        "[Comprehensive Inversion]: Lithospheric field of CIY4",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MLI/SW_OPER_MLI_VAL_2C_00000000T000000_99999999T999999_0401.ZIP",
    ),
    "MLI_SHA_2D": (
        "[Dedicated Chain]: Lithospheric field",
        " Swarm SCARF Dedicated Lithospheric Field Inversion chain, https://doi.org/10.5047/eps.2013.07.008 ",
        " Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MLI/SW_OPER_MLI_VAL_2D_00000000T000000_99999999T999999_0401.ZIP ",
    ),
    "MLI_SHA_2E": (
        "[Extended dedicated chain]: Lithospheric field",
        " Joint inversion of Swarm, CHAMP, and WDMAM data ",
        " https://swarm-diss.eo.esa.int/?do=download&file=swarm%2FLevel2longterm%2FMLI%2FSW_OPER_MLI_VAL_2E_00000000T000000_99999999T999999_0502.ZIP ",
    ),
    "MMA_SHA_2C-Primary": (
        "[Comprehensive Inversion]: Primary (external) magnetospheric field of CIY4",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MMA/SW_OPER_MMA_VAL_2C_20131201T000000_20180101T000000_0401.ZIP",
    ),
    "MMA_SHA_2C-Secondary": (
        "[Comprehensive Inversion]: Secondary (internal/induced) magnetospheric field of CIY4",
    ),
    "MMA_SHA_2F-Primary": (
        "[Fast-Track Product]: Primary (external) magnetospheric field",
        " Rapid modelling of the large-scale magnetospheric field from Swarm satellite data, https://doi.org/10.5047/eps.2013.09.003 ",
    ),
    "MMA_SHA_2F-Secondary": (
        "[Fast-Track Product]: Secondary (internal/induced) magnetospheric field",
    ),
    "MIO_SHA_2C-Primary": (
        "[Comprehensive Inversion]: Primary (external) ionospheric field of CIY4",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MIO/SW_OPER_MIO_VAL_2C_00000000T000000_99999999T999999_0401.ZIP ",
    ),
    "MIO_SHA_2C-Secondary": (
        "[Comprehensive Inversion]: Secondary (external/induced) ionospheric field of CIY4",
    ),
    "MIO_SHA_2D-Primary": (
        "[Dedicated Chain]: Primary (external) ionospheric field, DIFI",
        " Swarm SCARF dedicated ionospheric field inversion chain, https://doi.org/10.5047/eps.2013.08.006 ",
        " First results from the Swarm Dedicated Ionospheric Field Inversion chain, https://doi.org/10.1186/s40623-016-0481-6 ",
        " http://geomag.colorado.edu/difi-3 ",
        "Validation: ftp://swarm-diss.eo.esa.int/Level2longterm/MIO/SW_OPER_MIO_VAL_2D_20131201T000000_20171231T235959_0402.ZIP ",
    ),
    "MIO_SHA_2D-Secondary": (
        "[Dedicated Chain]: Secondary (external/induced) ionospheric field, DIFI",
    ),
    "AMPS": ("AMPS - associated magnetic field, https://github.com/klaundal/pyAMPS",),
    "MCO_SHA_2X": ("Alias for 'CHAOS-Core'",),
    "CHAOS": (
        "Alias for 'CHAOS-Core' + 'CHAOS-Static' + 'CHAOS-MMA-Primary' + 'CHAOS-MMA-Secondary'",
    ),
    "CHAOS-MMA": ("Alias for 'CHAOS-MMA-Primary' + 'CHAOS-MMA-Secondary'",),
    "MMA_SHA_2C": ("Alias for 'MMA_SHA_2C-Primary' + 'MMA_SHA_2C-Secondary'",),
    "MMA_SHA_2F": ("Alias for 'MMA_SHA_2F-Primary' + 'MMA_SHA_2F-Secondary'",),
    "MIO_SHA_2C": ("Alias for 'MIO_SHA_2C-Primary' + 'MIO_SHA_2C-Secondary'",),
    "MIO_SHA_2D": ("Alias for 'MIO_SHA_2D-Primary' + 'MIO_SHA_2D-Secondary'",),
    "SwarmCI": (
        "Alias for 'MCO_SHA_2C' + 'MLI_SHA_2C' + 'MIO_SHA_2C-Primary' + 'MIO_SHA_2C-Secondary' + 'MMA_SHA_2C-Primary' + 'MMA_SHA_2C-Secondary'",
    ),
}

DEPRECATED_MODELS = {
    "IGRF12": "Use IGRF instead.",
    "CHAOS-6-Core": "Use CHAOS-Core instead.",
    "CHAOS-6-Static": "Use CHAOS-Static instead.",
    "CHAOS-6-MMA-Primary": "Use CHAOS-MMA-Primary instead.",
    "CHAOS-6-MMA-Secondary": "Use CHAOS-MMA-Secondary instead.",
}

COLLECTION_REFERENCES = {
    "MAG": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-1b-product-definitions#MAGX_LR_1B_Product ",
    ),
    "MAG_HR": (
        "https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-1b-product-definitions#MAGX_HR_1B_Product ",
    ),
    "EFI": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-1b-product-definitions#EFIX_LP_1B_Product ",
    ),
    "IBI": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#IBIxTMS_2F ",
        " https://earth.esa.int/documents/10174/1514862/Swarm_L2_IBI_product_description ",
    ),
    "TEC": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#TECxTMS_2F ",
        " https://earth.esa.int/documents/10174/1514862/Swarm_Level-2_TEC_Product_Description ",
    ),
    "FAC": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#FAC_TMS_2F ",
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#FACxTMS_2F ",
        " https://earth.esa.int/documents/10174/1514862/Swarm_L2_FAC_single_product_description ",
        " https://earth.esa.int/documents/10174/1514862/Swarm-L2-FAC-Dual-Product-Description ",
    ),
    "EEF": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#EEFxTMS_2F ",
        " https://earth.esa.int/documents/10174/1514862/Swarm-Level-2-EEF-Product-Description ",
    ),
    "IPD": (
        " https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-2-product-definitions#IPDxIPR_2F ",
    ),
    "AUX_OBSH": ("https://doi.org/10.5047/eps.2013.07.011",),
    "AUX_OBSM": ("https://doi.org/10.5047/eps.2013.07.011",),
    "AUX_OBSS": ("https://doi.org/10.5047/eps.2013.07.011",),
    "VOBS_SW_1M": ("https://earth.esa.int/eogateway/activities/gvo",),
    "AEJ_LPL": ("https://earth.esa.int/eogateway/activities/swarm-aebs",),
    "AEJ_LPS": ("https://earth.esa.int/eogateway/activities/swarm-aebs",),
    "AEJ_PBL": ("https://earth.esa.int/eogateway/activities/swarm-aebs",),
    "AEJ_PBS": ("https://earth.esa.int/eogateway/activities/swarm-aebs",),
    "AOB_FAC": ("https://earth.esa.int/eogateway/activities/swarm-aebs",),
    "MIT_LP": (
        "https://earth.esa.int/eogateway/activities/plasmapause-related-boundaries-in-the-topside-ionosphere-as-derived-from-swarm-measurements",
    ),
    "MIT_TEC": (
        "https://earth.esa.int/eogateway/activities/plasmapause-related-boundaries-in-the-topside-ionosphere-as-derived-from-swarm-measurements",
    ),
    "PPI_FAC": (
        "https://earth.esa.int/eogateway/activities/plasmapause-related-boundaries-in-the-topside-ionosphere-as-derived-from-swarm-measurements",
    ),
    "MAG_CHAMP": ("https://doi.org/10.5880/GFZ.2.3.2019.004",),
    "MAG_CS": ("https://doi.org/10.1186/s40623-020-01171-9",),
    "MAG_GRACE": ("https://doi.org/10.1186/s40623-021-01373-9",),
    "MAG_GFO": ("https://doi.org/10.1186/s40623-021-01364-w",),
    "MAG_GFO_ML": ("https://doi.org/10.5880/GFZ.2.3.2023.001",),
    "EFI_IDM": (
        "https://earth.esa.int/eogateway/documents/20142/2860886/SLIDEM_Product_Definition.pdf",
    ),
    "MAG_GOCE": ("https://doi.org/10.5880/GFZ.2.3.2022.001",),
    "MAG_GOCE_ML": ("https://doi.org/10.5880/GFZ.2.3.2022.002",),
    "EFI_TIE": (
        "https://earth.esa.int/eogateway/activities/swarm-ion-temperature-estimation",
    ),
    "EFI_TCT02": (
        "https://earth.esa.int/eogateway/documents/20142/37627/swarm-EFI-TII-cross-track-flow-dataset-release-notes.pdf",
    ),
    "EFI_TCT16": (
        "https://earth.esa.int/eogateway/documents/20142/37627/swarm-EFI-TII-cross-track-flow-dataset-release-notes.pdf",
    ),
    "DNS_POD": ("https://swarmhandbook.earth.esa.int/catalogue/SW_DNSxPOD_2_",),
    "DNS_ACC": ("https://swarmhandbook.earth.esa.int/catalogue/SW_DNSxACC_2_",),
    "DNS_ACC_CHAMP": ("https://swarmhandbook.earth.esa.int/catalogue/CH_DNS_ACC_2_",),
    "DNS_ACC_GRACE": ("https://swarmhandbook.earth.esa.int/catalogue/GR_DNSxACC_2_",),
    "DNS_ACC_GFO": ("https://swarmhandbook.earth.esa.int/catalogue/GF_DNSxACC_2_",),
    "WND_ACC_CHAMP": ("https://swarmhandbook.earth.esa.int/catalogue/CH_WND_ACC_2_",),
    "WND_ACC_GRACE": ("https://swarmhandbook.earth.esa.int/catalogue/GR_WNDxACC_2_",),
    "WND_ACC_GFO": ("https://swarmhandbook.earth.esa.int/catalogue/GF_WNDxACC_2_",),
    "MM_CON_EPH_2_": ("https://swarmhandbook.earth.esa.int/catalogue/MM_CON_EPH_2_",),
}
for mission in ("SW", "OR", "CH", "CR", "CO"):
    for cadence in ("1M", "4M"):
        COLLECTION_REFERENCES[f"VOBS_{mission}_{cadence}"] = (
            "https://earth.esa.int/eogateway/activities/gvo",
        )

DATA_CITATIONS = {
    "AUX_OBSH": "ftp://ftp.nerc-murchison.ac.uk/geomag/Swarm/AUX_OBS/hour/README",
    "AUX_OBSM": "ftp://ftp.nerc-murchison.ac.uk/geomag/Swarm/AUX_OBS/minute/README",
    "AUX_OBSS": "ftp://ftp.nerc-murchison.ac.uk/geomag/Swarm/AUX_OBS/second/README",
}

IAGA_CODES = CONFIG_SWARM.get("IAGA_CODES")

VOBS_SITES = CONFIG_SWARM.get("VOBS_SITES")


class SwarmWPSInputs(WPSInputs):
    """Holds the set of inputs to be passed to the request template for Swarm"""

    NAMES = [
        "collection_ids",
        "model_expression",
        "begin_time",
        "end_time",
        "variables",
        "filters",
        "sampling_step",
        "response_type",
        "custom_shc",
        "ignore_cached_models",
    ]

    def __init__(
        self,
        collection_ids=None,
        model_expression=None,
        begin_time=None,
        end_time=None,
        variables=None,
        filters=None,
        sampling_step=None,
        response_type=None,
        custom_shc=None,
        ignore_cached_models=False,
    ):
        # Set up default values
        # Obligatory - these must be replaced before the request is made
        self.collection_ids = None if collection_ids is None else collection_ids
        self.begin_time = None if begin_time is None else begin_time
        self.end_time = None if end_time is None else end_time
        self.response_type = None if response_type is None else response_type
        # Optional - these defaults will be used if not replaced before the
        #            request is made
        self.model_expression = "" if model_expression is None else model_expression
        self.variables = [] if variables is None else variables
        self.filters = None if filters is None else filters
        self.sampling_step = None if sampling_step is None else sampling_step
        self.custom_shc = None if custom_shc is None else custom_shc
        self.ignore_cached_models = ignore_cached_models

    @property
    def collection_ids(self):
        return self._collection_ids

    @collection_ids.setter
    def collection_ids(self, collection_ids):
        if isinstance(collection_ids, dict) or collection_ids is None:
            self._collection_ids = collection_ids
        else:
            raise TypeError("collection_ids must be a dict")

    @staticmethod
    def _spacecraft_from_collection(collection):
        """Identify spacecraft (or ground observatory name) from collection name."""
        if "AUX_OBS" in collection or "VOBS" in collection:
            name = collection
        elif collection[:3] == "SW_":
            # 12th character in name, e.g. SW_OPER_MAGx_LR_1B
            sc = collection[11]
            sc_to_name = {"A": "Alpha", "B": "Bravo", "C": "Charlie"}
            name = sc_to_name.get(sc, "NSC")
        else:
            name = collection
        return name

    def set_collections(self, collections):
        """Restructure given list of collections as dict required by VirES."""
        # Build the output dictionary in the form:
        #  {"Alpha": ["SW..A..", "SW..A.."], "Bravo": ["SW..B.."], "NSC": [..]}
        if isinstance(collections, list):
            collection_dict = {}
            for collection in collections:
                tag = self._spacecraft_from_collection(collection)
                if tag in collection_dict.keys():
                    collection_dict[tag].append(collection)
                else:
                    collection_dict[tag] = [collection]
            self.collection_ids = collection_dict
        else:
            raise TypeError("collections must be a list")

    @property
    def model_expression(self):
        return self._model_expression

    @model_expression.setter
    def model_expression(self, model_expression):
        if isinstance(model_expression, str):
            self._model_expression = model_expression
        else:
            raise TypeError("model_expression must be a string")

    @property
    def ignore_cached_models(self):
        return self._ignore_cached_models

    @ignore_cached_models.setter
    def ignore_cached_models(self, value):
        if isinstance(value, bool):
            self._ignore_cached_models = value
        else:
            raise TypeError

    @property
    def begin_time(self):
        return self._begin_time

    @begin_time.setter
    def begin_time(self, begin_time):
        if isinstance(begin_time, datetime.datetime) or begin_time is None:
            self._begin_time = begin_time
        else:
            raise TypeError

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, end_time):
        if isinstance(end_time, datetime.datetime) or end_time is None:
            self._end_time = end_time
        else:
            raise TypeError

    @property
    def variables(self):
        return self._variables

    @variables.setter
    def variables(self, variables):
        if isinstance(variables, list):
            self._variables = variables
        else:
            raise TypeError

    @property
    def filters(self):
        return self._filters

    @filters.setter
    def filters(self, filters):
        if isinstance(filters, str) or filters is None:
            self._filters = filters
        else:
            raise TypeError

    @property
    def sampling_step(self):
        return self._sampling_step

    @sampling_step.setter
    def sampling_step(self, sampling_step):
        if isinstance(sampling_step, str) or sampling_step is None:
            self._sampling_step = sampling_step
        else:
            raise TypeError

    @property
    def response_type(self):
        return self._response_type

    @response_type.setter
    def response_type(self, response_type):
        if isinstance(response_type, str) or response_type is None:
            self._response_type = response_type
        else:
            raise TypeError

    @property
    def custom_shc(self):
        return self._custom_shc

    @custom_shc.setter
    def custom_shc(self, custom_shc):
        if isinstance(custom_shc, str) or custom_shc is None:
            self._custom_shc = custom_shc
        else:
            raise TypeError


class SwarmRequest(ClientRequest):
    """Handles the requests to and downloads from the server.

    Examples:

        Retrieve data::

            from viresclient import SwarmRequest
            # Set up connection with server
            request = SwarmRequest("https://vires.services/ows")
            # Set collection to use
            request.set_collection("SW_OPER_MAGA_LR_1B")
            # Set mix of products to fetch:
            #  measurements (variables from the given collection)
            #  models (magnetic model predictions at spacecraft sampling points)
            #  auxiliaries (variables available with any collection)
            request.set_products(
                measurements=["F", "B_NEC"],
                models=["CHAOS-Core"],
                auxiliaries=["QDLat", "QDLon"],
                sampling_step="PT10S"
            )
            # Fetch data from a given time interval
            data = request.get_between(
                start_time="2014-01-01T00:00",
                end_time="2014-01-01T01:00"
            )
            # Load the data as an xarray.Dataset
            ds = data.as_xarray()

        Check what data are available::

            request.available_collections(details=False)
            request.available_measurements("MAG")
            request.available_auxiliaries()
            request.available_models(details=False)

    Args:
        url (str):
        token (str):
        config (str or ClientConfig):
        logging_level (str):

    """

    MISSION_SPACECRAFTS = {
        "Swarm": ["A", "B", "C"],
        "GRACE": ["1", "2"],
        "GRACE-FO": ["1", "2"],
        "CryoSat-2": None,
        "GOCE": None,
    }

    CONJUNCTION_MISSION_SPACECRAFT_PAIRS = {
        (("Swarm", "A"), ("Swarm", "B")),
    }

    FILE_OPTIONS = {
        "MM_CON_EPH_2_:crossover": {
            "time_variable": "time_1",
            "secondary_time_variables": ["time_2"],
        },
        "MM_CON_EPH_2_:plane_alignment": {"time_variable": "time"},
    }

    COLLECTIONS = {
        "MAG": [
            *(f"SW_OPER_MAG{x}_LR_1B" for x in "ABC"),
            *(f"SW_FAST_MAG{x}_LR_1B" for x in "ABC"),
        ],
        "MAG_HR": [
            *(f"SW_OPER_MAG{x}_HR_1B" for x in "ABC"),
            *(f"SW_FAST_MAG{x}_HR_1B" for x in "ABC"),
        ],
        "EFI": [
            *(f"SW_OPER_EFI{x}_LP_1B" for x in "ABC"),
            *(f"SW_FAST_EFI{x}_LP_1B" for x in "ABC"),
        ],
        "EFI_IDM": [f"SW_PREL_EFI{x}IDM_2_" for x in "ABC"],
        "EFI_TIE": [f"SW_OPER_EFI{x}TIE_2_" for x in "ABC"],
        "EFI_TCT02": [f"SW_EXPT_EFI{x}_TCT02" for x in "ABC"],
        "EFI_TCT16": [f"SW_EXPT_EFI{x}_TCT16" for x in "ABC"],
        "IBI": [f"SW_OPER_IBI{x}TMS_2F" for x in "ABC"],
        "TEC": [f"SW_OPER_TEC{x}TMS_2F" for x in "ABC"],
        "FAC": [
            *(f"SW_OPER_FAC{x}TMS_2F" for x in "ABC_"),
            *(f"SW_FAST_FAC{x}TMS_2F" for x in "ABC"),
        ],
        "EEF": [f"SW_OPER_EEF{x}TMS_2F" for x in "ABC"],
        "IPD": [f"SW_OPER_IPD{x}IRR_2F" for x in "ABC"],
        "AEJ_LPL": [f"SW_OPER_AEJ{x}LPL_2F" for x in "ABC"],
        "AEJ_LPL:Quality": [f"SW_OPER_AEJ{x}LPL_2F:Quality" for x in "ABC"],
        "AEJ_LPS": [f"SW_OPER_AEJ{x}LPS_2F" for x in "ABC"],
        "AEJ_LPS:Quality": [f"SW_OPER_AEJ{x}LPS_2F:Quality" for x in "ABC"],
        "AEJ_PBL": [f"SW_OPER_AEJ{x}PBL_2F" for x in "ABC"],
        "AEJ_PBS": [f"SW_OPER_AEJ{x}PBS_2F" for x in "ABC"],
        "AEJ_PBS:GroundMagneticDisturbance": [
            f"SW_OPER_AEJ{x}PBS_2F:GroundMagneticDisturbance" for x in "ABC"
        ],
        "AOB_FAC": [f"SW_OPER_AOB{x}FAC_2F" for x in "ABC"],
        "AUX_OBSH": [
            "SW_OPER_AUX_OBSH2_",
            *[f"SW_OPER_AUX_OBSH2_:{code}" for code in IAGA_CODES],
        ],
        "AUX_OBSM": [
            "SW_OPER_AUX_OBSM2_",
            *[f"SW_OPER_AUX_OBSM2_:{code}" for code in IAGA_CODES],
        ],
        "AUX_OBSS": [
            "SW_OPER_AUX_OBSS2_",
            *[f"SW_OPER_AUX_OBSS2_:{code}" for code in IAGA_CODES],
        ],
        "VOBS_SW_1M": [
            "SW_OPER_VOBS_1M_2_",
            *[f"SW_OPER_VOBS_1M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_SW_4M": [
            "SW_OPER_VOBS_4M_2_",
            *[f"SW_OPER_VOBS_4M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CH_1M": [
            "CH_OPER_VOBS_1M_2_",
            *[f"CH_OPER_VOBS_1M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CR_1M": [
            "CR_OPER_VOBS_1M_2_",
            *[f"CR_OPER_VOBS_1M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_OR_1M": [
            "OR_OPER_VOBS_1M_2_",
            *[f"OR_OPER_VOBS_1M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CO_1M": [
            "CO_OPER_VOBS_1M_2_",
            *[f"CO_OPER_VOBS_1M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_OR_4M": [
            "OR_OPER_VOBS_4M_2_",
            *[f"OR_OPER_VOBS_4M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CH_4M": [
            "CH_OPER_VOBS_4M_2_",
            *[f"CH_OPER_VOBS_4M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CR_4M": [
            "CR_OPER_VOBS_4M_2_",
            *[f"CR_OPER_VOBS_4M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CO_4M": [
            "CO_OPER_VOBS_4M_2_",
            *[f"CO_OPER_VOBS_4M_2_:{site}" for site in VOBS_SITES],
        ],
        "VOBS_SW_1M:SecularVariation": [
            "SW_OPER_VOBS_1M_2_:SecularVariation",
            *[f"SW_OPER_VOBS_1M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_SW_4M:SecularVariation": [
            "SW_OPER_VOBS_4M_2_:SecularVariation",
            *[f"SW_OPER_VOBS_4M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CH_1M:SecularVariation": [
            "CH_OPER_VOBS_1M_2_:SecularVariation",
            *[f"CH_OPER_VOBS_1M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CR_1M:SecularVariation": [
            "CR_OPER_VOBS_1M_2_:SecularVariation",
            *[f"CR_OPER_VOBS_1M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_OR_1M:SecularVariation": [
            "OR_OPER_VOBS_1M_2_:SecularVariation",
            *[f"OR_OPER_VOBS_1M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CO_1M:SecularVariation": [
            "CO_OPER_VOBS_1M_2_:SecularVariation",
            *[f"CO_OPER_VOBS_1M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_OR_4M:SecularVariation": [
            "OR_OPER_VOBS_4M_2_:SecularVariation",
            *[f"OR_OPER_VOBS_4M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CH_4M:SecularVariation": [
            "CH_OPER_VOBS_4M_2_:SecularVariation",
            *[f"CH_OPER_VOBS_4M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CR_4M:SecularVariation": [
            "CR_OPER_VOBS_4M_2_:SecularVariation",
            *[f"CR_OPER_VOBS_4M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "VOBS_CO_4M:SecularVariation": [
            "CO_OPER_VOBS_4M_2_:SecularVariation",
            *[f"CO_OPER_VOBS_4M_2_:SecularVariation:{site}" for site in VOBS_SITES],
        ],
        "MIT_LP": [f"SW_OPER_MIT{x}_LP_2F" for x in "ABC"],
        "MIT_LP:ID": [f"SW_OPER_MIT{x}_LP_2F:ID" for x in "ABC"],
        "MIT_TEC": [f"SW_OPER_MIT{x}TEC_2F" for x in "ABC"],
        "MIT_TEC:ID": [f"SW_OPER_MIT{x}TEC_2F:ID" for x in "ABC"],
        "PPI_FAC": [f"SW_OPER_PPI{x}FAC_2F" for x in "ABC"],
        "PPI_FAC:ID": [f"SW_OPER_PPI{x}FAC_2F:ID" for x in "ABC"],
        # Multi-mission magnetic products
        "MAG_CHAMP": ["CH_ME_MAG_LR_3"],
        "MAG_CS": ["CS_OPER_MAG"],
        "MAG_GRACE": ["GRACE_A_MAG", "GRACE_B_MAG"],
        "MAG_GFO": ["GF1_OPER_FGM_ACAL_CORR", "GF2_OPER_FGM_ACAL_CORR"],
        "MAG_GFO_ML": ["GF1_MAG_ACAL_CORR_ML", "GF2_MAG_ACAL_CORR_ML"],
        "MAG_GOCE": ["GO_MAG_ACAL_CORR"],
        "MAG_GOCE_ML": ["GO_MAG_ACAL_CORR_ML"],
        # Swarm spacecraft positions
        "MOD_SC": [
            *(f"SW_OPER_MOD{x}_SC_1B" for x in "ABC"),
            *(f"SW_FAST_MOD{x}_SC_1B" for x in "ABC"),
        ],
        # Swarm thermospheric density products:
        "DNS_POD": [f"SW_OPER_DNS{spacecraft}POD_2_" for spacecraft in "ABC"],
        "DNS_ACC": [f"SW_OPER_DNS{spacecraft}ACC_2_" for spacecraft in "ABC"],
        # TOLEOS thermospheric density and crosswind products:
        "DNS_ACC_CHAMP": ["CH_OPER_DNS_ACC_2_"],
        "DNS_ACC_GRACE": ["GR_OPER_DNS1ACC_2_", "GR_OPER_DNS2ACC_2_"],
        "DNS_ACC_GFO": ["GF_OPER_DNS1ACC_2_"],  # empty GF_OPER_DNS2ACC_2_ exists
        "WND_ACC_CHAMP": ["CH_OPER_WND_ACC_2_"],
        "WND_ACC_GRACE": ["GR_OPER_WND1ACC_2_", "GR_OPER_WND2ACC_2_"],
        "WND_ACC_GFO": ["GF_OPER_WND1ACC_2_"],  # empty GF_OPER_WND2ACC_2_ exists
        # TOLEOS conjunctions
        "MM_CON_EPH_2_:crossover": ["MM_OPER_CON_EPH_2_:crossover"],
        "MM_CON_EPH_2_:plane_alignment": ["MM_OPER_CON_EPH_2_:plane_alignment"],
    }

    OBS_COLLECTIONS = [
        "SW_OPER_AUX_OBSH2_",
        "SW_OPER_AUX_OBSM2_",
        "SW_OPER_AUX_OBSS2_",
        "SW_OPER_VOBS_1M_2_",
        "SW_OPER_VOBS_4M_2_",
        "CH_OPER_VOBS_1M_2_",
        "CR_OPER_VOBS_1M_2_",
        "OR_OPER_VOBS_1M_2_",
        "CO_OPER_VOBS_1M_2_",
        "OR_OPER_VOBS_4M_2_",
        "CH_OPER_VOBS_4M_2_",
        "CR_OPER_VOBS_4M_2_",
        "CO_OPER_VOBS_4M_2_",
        "SW_OPER_VOBS_1M_2_:SecularVariation",
        "SW_OPER_VOBS_4M_2_:SecularVariation",
        "CH_OPER_VOBS_1M_2_:SecularVariation",
        "CR_OPER_VOBS_1M_2_:SecularVariation",
        "OR_OPER_VOBS_1M_2_:SecularVariation",
        "CO_OPER_VOBS_1M_2_:SecularVariation",
        "OR_OPER_VOBS_4M_2_:SecularVariation",
        "CH_OPER_VOBS_4M_2_:SecularVariation",
        "CR_OPER_VOBS_4M_2_:SecularVariation",
        "CO_OPER_VOBS_4M_2_:SecularVariation",
    ]

    # These are not necessarily real sampling steps, but are good enough to use
    # for splitting long requests into chunks
    COLLECTION_SAMPLING_STEPS = {
        "MAG": "PT1S",
        "MAG_HR": "PT0.019S",  # approx 50Hz (the sampling is not exactly 50Hz)
        "EFI": "PT0.5S",
        "EFI_IDM": "PT0.5S",
        "EFI_TIE": "PT0.5S",
        "EFI_TCT02": "PT0.5S",
        "EFI_TCT16": "PT0.0625S",
        "IBI": "PT1S",
        "TEC": "PT1S",  # Actually more complicated
        "FAC": "PT1S",
        "EEF": "PT90M",
        "IPD": "PT1S",
        "AEJ_LPL": "PT15.6S",
        "AEJ_LPS": "PT1S",
        "AUX_OBSH": "PT60M",
        "AUX_OBSM": "PT60S",
        "AUX_OBSS": "PT1S",
        "VOBS_SW_1M": "P31D",
        "VOBS_CH_1M": "P31D",
        "VOBS_CR_1M": "P31D",
        "VOBS_OR_1M": "P31D",
        "VOBS_CO_1M": "P31D",
        "VOBS_OR_4M": "P122D",
        "VOBS_SW_4M": "P122D",
        "VOBS_CH_4M": "P122D",
        "VOBS_CR_4M": "P122D",
        "VOBS_CO_4M": "P122D",
        "VOBS_SW_1M:SecularVariation": "P31D",
        "VOBS_CH_1M:SecularVariation": "P31D",
        "VOBS_CR_1M:SecularVariation": "P31D",
        "VOBS_OR_1M:SecularVariation": "P31D",
        "VOBS_CO_1M:SecularVariation": "P31D",
        "VOBS_OR_4M:SecularVariation": "P122D",
        "VOBS_SW_4M:SecularVariation": "P122D",
        "VOBS_CH_4M:SecularVariation": "P122D",
        "VOBS_CR_4M:SecularVariation": "P122D",
        "VOBS_CO_4M:SecularVariation": "P122D",
        "MIT_LP": "PT20M",
        "MIT_LP:ID": "PT20M",
        "MIT_TEC": "PT20M",
        "MIT_TEC:ID": "PT20M",
        "PPI_FAC": "PT20M",
        "PPI_FAC:ID": "PT20M",
        "DNS_POD": "PT30S",
        "DNS_ACC": "PT10S",
        "DNS_ACC_CHAMP": "PT10S",
        "DNS_ACC_GRACE": "PT10S",
        "DNS_ACC_GFO": "PT10S",
        "WND_ACC_CHAMP": "PT10S",
        "WND_ACC_GRACE": "PT10S",
        "WND_ACC_GFO": "PT10S",
        "MM_CON_EPH_2_:crossover": "PT20M",
        "MM_CON_EPH_2_:plane_alignment": "P1D",
    }

    PRODUCT_VARIABLES = {
        "MAG": [
            "F",
            "dF_Sun",
            "dF_AOCS",
            "dF_other",
            "F_error",
            "B_VFM",
            "B_NEC",
            "dB_Sun",
            "dB_AOCS",
            "dB_other",
            "B_error",
            "q_NEC_CRF",
            "Att_error",
            "Flags_F",
            "Flags_B",
            "Flags_q",
            "Flags_Platform",
            "ASM_Freq_Dev",
        ],
        "MAG_HR": [  # NOTE: F is calculated on the fly from B_NEC (F = |B_NEC|)
            "F",
            "B_VFM",
            "B_NEC",
            "dB_Sun",
            "dB_AOCS",
            "dB_other",
            "B_error",
            "q_NEC_CRF",
            "Att_error",
            "Flags_B",
            "Flags_q",
            "Flags_Platform",
        ],
        "EFI": [
            "U_orbit",
            "Ne",
            "Ne_error",
            "Te",
            "Te_error",
            "Vs",
            "Vs_error",
            "Flags_LP",
            "Flags_Ne",
            "Flags_Te",
            "Flags_Vs",
        ],
        "EFI_IDM": [
            "Latitude_GD",
            "Longitude_GD",
            "Height_GD",
            "Radius_GC",
            "Latitude_QD",
            "MLT_QD",
            "V_sat_nec",
            "M_i_eff",
            "M_i_eff_err",
            "M_i_eff_Flags",
            "M_i_eff_tbt_model",
            "V_i",
            "V_i_err",
            "V_i_Flags",
            "V_i_raw",
            "N_i",
            "N_i_err",
            "N_i_Flags",
            "A_fp",
            "R_p",
            "T_e",
            "Phi_sc",
        ],
        "EFI_TIE": [
            "Latitude_GD",
            "Longitude_GD",
            "Height_GD",
            "Radius_GC",
            "Latitude_QD",
            "MLT_QD",
            "Tn_msis",
            "Te_adj_LP",
            "Ti_meas_drift",
            "Ti_model_drift",
            "Flag_ti_meas",
            "Flag_ti_model",
        ],
        "EFI_TCT02": [  # identical to EFI_TCT16
            "VsatC",
            "VsatE",
            "VsatN",
            "Bx",
            "By",
            "Bz",
            "Ehx",
            "Ehy",
            "Ehz",
            "Evx",
            "Evy",
            "Evz",
            "Vicrx",
            "Vicry",
            "Vicrz",
            "Vixv",
            "Vixh",
            "Viy",
            "Viz",
            "Vixv_error",
            "Vixh_error",
            "Viy_error",
            "Viz_error",
            "Latitude_QD",
            "MLT_QD",
            "Calibration_flags",
            "Quality_flags",
        ],
        "EFI_TCT16": [  # identical to EFI_TCT02
            "VsatC",
            "VsatE",
            "VsatN",
            "Bx",
            "By",
            "Bz",
            "Ehx",
            "Ehy",
            "Ehz",
            "Evx",
            "Evy",
            "Evz",
            "Vicrx",
            "Vicry",
            "Vicrz",
            "Vixv",
            "Vixh",
            "Viy",
            "Viz",
            "Vixv_error",
            "Vixh_error",
            "Viy_error",
            "Viz_error",
            "Latitude_QD",
            "MLT_QD",
            "Calibration_flags",
            "Quality_flags",
        ],
        "IBI": [
            "Bubble_Index",
            "Bubble_Probability",
            "Flags_Bubble",
            "Flags_F",
            "Flags_B",
            "Flags_q",
        ],
        "TEC": [
            "GPS_Position",
            "LEO_Position",
            "PRN",
            "L1",
            "L2",
            "P1",
            "P2",
            "S1",
            "S2",
            "Elevation_Angle",
            "Absolute_VTEC",
            "Absolute_STEC",
            "Relative_STEC",
            "Relative_STEC_RMS",
            "DCB",
            "DCB_Error",
        ],
        "FAC": [
            "IRC",
            "IRC_Error",
            "FAC",
            "FAC_Error",
            "Flags",
            "Flags_F",
            "Flags_B",
            "Flags_q",
        ],
        "EEF": ["EEF", "EEJ", "RelErr", "Flags"],
        "IPD": [
            "Ne",
            "Te",
            "Background_Ne",
            "Foreground_Ne",
            "PCP_flag",
            "Grad_Ne_at_100km",
            "Grad_Ne_at_50km",
            "Grad_Ne_at_20km",
            "Grad_Ne_at_PCP_edge",
            "ROD",
            "RODI10s",
            "RODI20s",
            "delta_Ne10s",
            "delta_Ne20s",
            "delta_Ne40s",
            "Num_GPS_satellites",
            "mVTEC",
            "mROT",
            "mROTI10s",
            "mROTI20s",
            "IBI_flag",
            "Ionosphere_region_flag",
            "IPIR_index",
            "Ne_quality_flag",
            "TEC_STD",
        ],
        "AEJ_LPL": ["Latitude_QD", "Longitude_QD", "MLT_QD", "J_NE", "J_QD"],
        "AEJ_LPL:Quality": ["RMS_misfit", "Confidence"],
        "AEJ_LPS": [
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "J_CF_NE",
            "J_DF_NE",
            "J_CF_SemiQD",
            "J_DF_SemiQD",
            "J_R",
        ],
        "AEJ_LPS:Quality": ["RMS_misfit", "Confidence"],
        "AEJ_PBL": [
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "J_QD",
            "Flags",
            "PointType",
        ],
        "AEJ_PBS": [
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "J_DF_SemiQD",
            "Flags",
            "PointType",
        ],
        "AEJ_PBS:GroundMagneticDisturbance": ["B_NE"],
        "AOB_FAC": [
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "Boundary_Flag",
            "Quality",
            "Pair_Indicator",
        ],
        "AUX_OBSH": ["B_NEC", "F", "IAGA_code", "Quality", "ObsIndex"],
        "AUX_OBSM": ["B_NEC", "F", "IAGA_code", "Quality"],
        "AUX_OBSS": ["B_NEC", "F", "IAGA_code", "Quality"],
        "VOBS_SW_1M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CH_1M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CR_1M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_OR_1M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CO_1M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_OR_4M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_SW_4M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CH_4M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CR_4M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_CO_4M": ["SiteCode", "B_CF", "B_OB", "sigma_CF", "sigma_OB"],
        "VOBS_SW_1M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CH_1M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CR_1M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_OR_1M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CO_1M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_OR_4M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_SW_4M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CH_4M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CR_4M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "VOBS_CO_4M:SecularVariation": ["SiteCode", "B_SV", "sigma_SV"],
        "MIT_LP": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "Ne",
            "Te",
            "Depth",
            "DR",
            "Width",
            "dL",
            "PW_Gradient",
            "EW_Gradient",
            "Quality",
        ],
        "MIT_LP:ID": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "Ne",
            "Te",
            "Position_Quality",
            "PointType",
        ],
        "MIT_TEC": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "TEC",
            "Depth",
            "DR",
            "Width",
            "dL",
            "PW_Gradient",
            "EW_Gradient",
            "Quality",
        ],
        "MIT_TEC:ID": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "TEC",
            "Position_Quality",
            "PointType",
        ],
        "PPI_FAC": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "Sigma",
            "PPI",
            "dL",
            "Quality",
        ],
        "PPI_FAC:ID": [
            "Counter",
            "Latitude_QD",
            "Longitude_QD",
            "MLT_QD",
            "L_value",
            "SZA",
            "Position_Quality",
            "PointType",
        ],
        "MAG_CHAMP": [
            "F",
            "B_VFM",
            "B_NEC",
            "Flags_Position",
            "Flags_B",
            "Flags_q",
            "Mode_q",
            "q_ICRF_CRF",
        ],
        "MAG_CS": [
            "F",
            "B_NEC",
            "B_mod_NEC",
            "B_NEC1",
            "B_NEC2",
            "B_NEC3",
            "B_FGM1",
            "B_FGM2",
            "B_FGM3",
            "q_NEC_CRF",
            "q_error",
        ],
        "MAG_GRACE": [
            "F",
            "B_NEC",
            "B_NEC_raw",
            "B_FGM",
            "q_NEC_CRF",
            "q_error",
        ],
        "MAG_GFO": [
            "F",
            "B_NEC",
            "B_FGM",
            "dB_MTQ_FGM",
            "dB_XI_FGM",
            "dB_NY_FGM",
            "dB_BT_FGM",
            "dB_ST_FGM",
            "dB_SA_FGM",
            "dB_BAT_FGM",
            "q_NEC_FGM",
            "B_FLAG",
        ],
        "MAG_GFO_ML": [
            "F",
            "B_MAG",
            "B_NEC",
            "q_NEC_FGM",
            "B_FLAG",
            "KP_DST_FLAG",
            "Latitude_QD",
            "Longitude_QD",
        ],
        "MAG_GOCE": [
            "F",
            "B_MAG",
            "B_NEC",
            "dB_MTQ_SC",
            "dB_XI_SC",
            "dB_NY_SC",
            "dB_BT_SC",
            "dB_ST_SC",
            "dB_SA_SC",
            "dB_BAT_SC",
            "dB_HK_SC",
            "dB_BLOCK_CORR",
            "q_SC_NEC",
            "q_MAG_SC",
            "B_FLAG",
        ],
        "MAG_GOCE_ML": [
            "F",
            "B_MAG",
            "B_NEC",
            "q_FGM_NEC",
            "B_FLAG",
            "MAGNETIC_ACTIVITY_FLAG",
            "NaN_FLAG",
            "Latitude_QD",
            "Longitude_QD",
        ],
        "MOD_SC": [],
        "DNS_POD": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "Height_GD",
            "local_solar_time",
            "density",
            "density_orbitmean",
            "validity_flag",
        ],
        "DNS_ACC": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "Height_GD",
            "density",
            "local_solar_time",
        ],
        "DNS_ACC_CHAMP": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "density",
            "density_orbitmean",
            "local_solar_time",
            "validity_flag",
            "validity_flag_orbitmean",
        ],
        "DNS_ACC_GRACE": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "density",
            "density_orbitmean",
            "local_solar_time",
            "validity_flag",
            "validity_flag_orbitmean",
        ],
        "DNS_ACC_GFO": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "density",
            "density_orbitmean",
            "local_solar_time",
            "validity_flag",
            "validity_flag_orbitmean",
        ],
        "WND_ACC_CHAMP": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "crosswind",
            "crosswind_direction",
            "local_solar_time",
            "validity_flag",
        ],
        "WND_ACC_GRACE": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "crosswind",
            "crosswind_direction",
            "local_solar_time",
            "validity_flag",
        ],
        "WND_ACC_GFO": [
            "Height_GD",
            "Latitude_GD",
            "Longitude_GD",
            "crosswind",
            "crosswind_direction",
            "local_solar_time",
            "validity_flag",
        ],
        "MM_CON_EPH_2_:crossover": [
            "time_1",
            "time_2",
            "time_difference",
            "satellite_1",
            "satellite_2",
            "latitude",
            "longitude",
            "altitude_1",
            "altitude_2",
            "magnetic_latitude",
            "magnetic_longitude",
            "local_solar_time_1",
            "local_solar_time_2",
        ],
        "MM_CON_EPH_2_:plane_alignment": [
            "time",
            "altitude_1",
            "altitude_2",
            "ltan_1",
            "ltan_2",
            "ltan_rate_1",
            "ltan_rate_2",
            "satellite_1",
            "satellite_2",
        ],
    }

    AUXILIARY_VARIABLES = [
        "Timestamp",
        "Latitude",
        "Longitude",
        "Radius",
        "Spacecraft",
        "OrbitDirection",
        "QDOrbitDirection",
        "SyncStatus",
        "Kp10",
        "Kp",
        "Dst",
        "F107",
        "F107_avg81d",
        "F107_avg81d_count",
        "IMF_BY_GSM",
        "IMF_BZ_GSM",
        "IMF_V",
        "F10_INDEX",
        "OrbitSource",
        "OrbitNumber",
        "AscendingNodeTime",
        "AscendingNodeLongitude",
        "QDLat",
        "QDLon",
        "QDBasis",
        "MLT",
        "SunDeclination",
        "SunHourAngle",
        "SunRightAscension",
        "SunAzimuthAngle",
        "SunZenithAngle",
        "SunLongitude",
        "SunVector",
        "DipoleAxisVector",
        "NGPLatitude",
        "NGPLongitude",
        "DipoleTiltAngle",
        "dDst",
    ]

    MAGNETIC_MODEL_VARIABLES = {
        "F": "F",
        "B_NEC": "B_NEC",
        "B_NEC1": "B_NEC",
        "B_NEC2": "B_NEC",
        "B_NEC3": "B_NEC",
    }

    MAGNETIC_MODELS = [
        "IGRF",
        "IGRF12",
        "LCS-1",
        "MF7",
        "CHAOS-Core",
        "CHAOS-Static",
        "CHAOS-MMA-Primary",
        "CHAOS-MMA-Secondary",
        "CHAOS-6-Core",
        "CHAOS-6-Static",
        "CHAOS-6-MMA-Primary",
        "CHAOS-6-MMA-Secondary",
        "MCO_SHA_2C",
        "MCO_SHA_2D",
        "MLI_SHA_2C",
        "MLI_SHA_2D",
        "MLI_SHA_2E",
        "MMA_SHA_2C-Primary",
        "MMA_SHA_2C-Secondary",
        "MMA_SHA_2F-Primary",
        "MMA_SHA_2F-Secondary",
        "MIO_SHA_2C-Primary",
        "MIO_SHA_2C-Secondary",
        "MIO_SHA_2D-Primary",
        "MIO_SHA_2D-Secondary",
        "AMPS",
        "MCO_SHA_2X",
        "CHAOS",
        "CHAOS-MMA",
        "MMA_SHA_2C",
        "MMA_SHA_2F",
        "MIO_SHA_2C",
        "MIO_SHA_2D",
        "SwarmCI",
    ]

    def __init__(self, url=None, token=None, config=None, logging_level="NO_LOGGING"):
        super().__init__(url, token, config, logging_level, server_type="Swarm")

        self._available = self._get_available_data()
        self._request_inputs = SwarmWPSInputs()
        self._templatefiles = TEMPLATE_FILES
        self._filterlist = []
        self._supported_filetypes = ("csv", "cdf")
        self._collection_list = None

    @classmethod
    def _get_available_data(cls):
        # Build the reverse mapping: "SW_OPER_MAGA_LR_1B": "MAG" etc
        collections_to_keys = {}
        for key, collections in cls.COLLECTIONS.items():
            collections_to_keys.update({collection: key for collection in collections})

        return {
            "collections": cls.COLLECTIONS,
            "collections_to_keys": collections_to_keys,
            "collection_sampling_steps": cls.COLLECTION_SAMPLING_STEPS,
            "measurements": cls.PRODUCT_VARIABLES,
            "models": cls.MAGNETIC_MODELS,
            "model_variables": cls.MAGNETIC_MODEL_VARIABLES,
            "auxiliaries": cls.AUXILIARY_VARIABLES,
        }

    @staticmethod
    def _parse_models_input(models=None):
        """Verify and parse models input.

        Args:
            models (list/dict): User-provided values

        Returns:
            list: model_ids, list of model_id strings
            str: model_expression_string to be passed to the server
        """
        models = [] if models is None else models
        # Convert input to OrderedDict
        #  e.g. {"model_name": "model_expression", ..}
        # Check if models input is basic list of strings,
        #  If not, then handle inputs given as dicts or list of tuples
        if isinstance(models, list) and all(isinstance(item, str) for item in models):
            # Convert the models list to an OrderedDict
            model_expressions = OrderedDict()
            for model in models:
                model_id, _, model_expression = (
                    s.strip() for s in model.partition("=")
                )
                model_expressions[model_id] = model_expression
        else:
            try:
                model_expressions = OrderedDict(models)
                # Check that everything is a string
                if not all(
                    isinstance(item, str)
                    for item in [*model_expressions.values()]
                    + [*model_expressions.keys()]
                ):
                    raise ValueError
            except ValueError:
                raise ValueError("Invalid models input!")
        # TODO: Verify input model names
        #  (use self._available["models"])
        # Create the combined model expression string passed to the request
        model_expression_string = ""
        for model_id, model_expression in model_expressions.items():
            if model_expression == "":
                s = model_id
            else:
                s = "=".join([model_id, model_expression])
            model_expression_string = ",".join([model_expression_string, s])
        model_ids = list(s.strip("'\"") for s in model_expressions.keys())
        return model_ids, model_expression_string[1:]

    def available_collections(self, groupname=None, details=True):
        """Show details of available collections.

        Args:
            groupname (str): one of: ("MAG", "EFI", etc.)
            details (bool): If True then print a nice output.
                If False then return a dict of available collections.

        """
        # Shorter form of the available collections,
        # without all the individual SiteCodes
        collections_short = self._available["collections"].copy()
        collections_short["AUX_OBSS"] = ["SW_OPER_AUX_OBSS2_"]
        collections_short["AUX_OBSM"] = ["SW_OPER_AUX_OBSM2_"]
        collections_short["AUX_OBSH"] = ["SW_OPER_AUX_OBSH2_"]
        for mission in ("SW", "OR", "CH", "CR", "CO"):
            for cadence in ("1M", "4M"):
                collections_short[f"VOBS_{mission}_{cadence}"] = [
                    f"{mission}_OPER_VOBS_{cadence}_2_"
                ]
                collections_short[f"VOBS_{mission}_{cadence}:SecularVariation"] = [
                    f"{mission}_OPER_VOBS_{cadence}_2_:SecularVariation"
                ]

        def _filter_collections(groupname):
            """Reduce the full list to just one group, e.g. "MAG"""
            if groupname:
                groups = list(collections_short.keys())
                if groupname in groups:
                    return {groupname: collections_short[groupname]}
                else:
                    raise ValueError("Invalid collection group name")
            else:
                return collections_short

        collections_filtered = _filter_collections(groupname)
        if details:
            print("General References:")
            for i in REFERENCES["General Swarm"]:
                print(i)
            print()
            for key, val in collections_filtered.items():
                print(key)
                for i in val:
                    print("  ", i)
                refs = COLLECTION_REFERENCES.get(key, ("No reference...",))
                for ref in refs:
                    print(ref)
                print()
        else:
            return collections_filtered

    def available_measurements(self, collection=None):
        """Returns a list of the available measurements for the chosen collection.

        Args:
            collection (str): one of: ("MAG", "EFI", "IBI", "TEC", "FAC", "EEF")

        """
        keys = list(self._available["measurements"].keys())
        if collection in keys:
            collection_key = collection
            return self._available["measurements"][collection_key]
        elif collection in self._available["collections_to_keys"]:
            collection_key = self._available["collections_to_keys"][collection]
            return self._available["measurements"][collection_key]
        elif collection is None:
            return self._available["measurements"]
        else:
            raise Exception(
                "collection must be one of {}\nor\n{}".format(
                    ", ".join(keys), "\n".join(self._available["collections_to_keys"])
                )
            )

    def available_models(self, param=None, details=True, nice_output=True):
        """Show details of avalable models.

        If details is True, return a dictionary of model names and details.
        If nice_output is True, the dictionary is printed nicely.
        If details is False, return a list of model names.
        If param is set, filter to only return entries including this

        Note:
            |  F = Fast-Track Products
            |  C = Comprehensive Inversion
            |  D = Dedicated Chain
            |  MCO = Core / main
            |  MLI = Lithosphere
            |  MMA = Magnetosphere
            |  MIO = Ionosphere

        Args:
            param (str): one of "F C D MCO MLI MMA MIO"
            details (bool): True for a dict of details, False for a brief list
            nice_output (bool): If True, just print the dict nicely

        """

        def filter_by_param(d, param):
            if param in ("F", "C", "D"):
                param = "2" + param
            return [i for i in d if param in i]

        # get all models provided by the server
        models_info = self.get_model_info()

        # keep only models really provided by the server
        d = [
            model_name
            for model_name in self._available["models"]
            if model_name in models_info
        ]

        # Filter the dict/list to only include those that contain param
        if param is not None:
            d = filter_by_param(d, param)

        if details:
            d = {
                model_name: {
                    "description": MODEL_REFERENCES[model_name],
                    "details": models_info[model_name],
                }
                for model_name in d
            }

        if nice_output and details:
            d = OrderedDict(sorted(d.items()))
            for model_name, desc_details in d.items():
                print(model_name, "=", desc_details["details"]["expression"])
                print("  START:", desc_details["details"]["validity"]["start"])
                print("  END:  ", desc_details["details"]["validity"]["end"])
                print("DESCRIPTION:")
                for line in desc_details["description"]:
                    print(line)
                print("SOURCES:")
                for line in desc_details["details"]["sources"]:
                    print(" ", line)
                print()
        else:
            return d

    def available_auxiliaries(self):
        """Returns a list of the available auxiliary parameters."""
        return self._available["auxiliaries"]

    def available_observatories(
        self, collection, start_time=None, end_time=None, details=False, verbose=True
    ):
        """Get list of available observatories from server.

        Search availability by collection, one of::

            "SW_OPER_AUX_OBSH2_"
            "SW_OPER_AUX_OBSM2_"
            "SW_OPER_AUX_OBSS2_"

        Examples:

            ::

                from viresclient import SwarmRequest
                request = SwarmRequest()
                # For a list of observatories available:
                request.available_observatories("SW_OPER_AUX_OBSM2_")
                # For a DataFrame also containing availability start and end times:
                request.available_observatories("SW_OPER_AUX_OBSM2_", details=True)
                # For available observatories during a given time period:
                request.available_observatories(
                    "SW_OPER_AUX_OBSM2_", "2013-01-01", "2013-02-01"
                )

        Args:
            collection (str): OBS collection name, e.g. "SW_OPER_AUX_OBSM2\\_"
            start_time (datetime / ISO_8601 string)
            end_time (datetime / ISO_8601 string)
            details (bool): returns DataFrame if True
            verbose (bool): Notify with special data terms

        Returns:
            list or DataFrame: IAGA codes (and start/end times)

        """

        def _request_get_observatories(collection=None, start_time=None, end_time=None):
            """Make the get_observatories request to the server"""
            templatefile = TEMPLATE_FILES["get_observatories"]
            template = JINJA2_ENVIRONMENT.get_template(templatefile)
            request = template.render(
                collection_id=collection,
                begin_time=start_time,
                end_time=end_time,
                response_type="text/csv",
            ).encode("UTF-8")
            response = self._get(request, asynchronous=False, show_progress=False)
            return response

        def _csv_to_df(csv_data):
            """Convert bytes data to pandas dataframe"""
            return read_csv(StringIO(str(csv_data, "utf-8")))

        if collection not in self.OBS_COLLECTIONS:
            raise ValueError(
                f"Invalid collection: {collection}. Must be one of: {self.OBS_COLLECTIONS}."
            )
        if start_time and end_time:
            start_time = parse_datetime(start_time)
            end_time = parse_datetime(end_time)
        else:
            start_time, end_time = None, None

        if verbose:
            self._detect_AUX_OBS([collection])
        response = _request_get_observatories(collection, start_time, end_time)
        df = _csv_to_df(response)
        if details:
            return df
        else:
            # note: "IAGACode" has been renamed to "site" in VirES 3.5
            key = "IAGACode" if "IAGACode" in df.keys() else "site"
            return list(df[key])

    def _detect_AUX_OBS(self, collections):
        # Identify collection types present
        collection_types_requested = {
            self._available["collections_to_keys"].get(collection)
            for collection in collections
        }
        # Output notification for each of aux_type
        for aux_type in ["AUX_OBSH", "AUX_OBSM", "AUX_OBSS"]:
            if aux_type in collection_types_requested:
                output_text = dedent(
                    f"""
                Accessing INTERMAGNET and/or WDC data
                Check usage terms at {DATA_CITATIONS.get(aux_type)}
                """
                )
                tqdm.write(output_text)

    def set_collection(self, *args, verbose=True):
        """Set the collection(s) to use.

        Args:
            (str): one or several from .available_collections()
            verbose (bool): Notify if special data terms

        """
        collections = [*args]
        for collection in collections:
            if not isinstance(collection, str):
                raise TypeError(f"{collection} invalid. Must be string.")
            if collection not in self._available["collections_to_keys"]:
                raise ValueError(
                    "Invalid collection: {}. "
                    "Check available with SwarmRequest().available_collections()".format(
                        collection
                    )
                )
        if verbose:
            self._detect_AUX_OBS(collections)
        self._collection_list = collections
        self._request_inputs.set_collections(collections)

        # type specific file options
        self._file_options = (
            self.FILE_OPTIONS.get(self._available["collections_to_keys"][collection])
            or {}
        )

        return self

    def set_products(
        self,
        measurements=None,
        models=None,
        custom_model=None,
        auxiliaries=None,
        residuals=False,
        sampling_step=None,
        ignore_cached_models=False,
    ):
        """Set the combination of products to retrieve.

        If residuals=True then just get the measurement-model residuals,
        otherwise get both measurement and model values.

        Args:
            measurements (list(str)): from .available_measurements(collection_key)
            models (list(str)/dict): from .available_models() or defineable with custom expressions
            custom_model (str): path to a custom model in .shc format
            auxiliaries (list(str)): from .available_auxiliaries()
            residuals (bool): True if only returning measurement-model residual
            sampling_step (str): ISO_8601 duration, e.g. 10 seconds: PT10S, 1 minute: PT1M
            ignore_cached_models (bool): True if cached models should be ignored and calculated on-the-fly

        """
        if self._collection_list is None:
            raise Exception("Must run .set_collection() first.")
        measurements = [] if measurements is None else measurements
        models = [] if models is None else models
        model_variables = self._available["model_variables"]
        auxiliaries = [] if auxiliaries is None else auxiliaries
        # If inputs are strings (when providing only one parameter)
        #  put them in lists
        if isinstance(measurements, str):
            measurements = [measurements]
        if isinstance(models, str):
            models = [models]
        if isinstance(auxiliaries, str):
            auxiliaries = [auxiliaries]
        # print warning for deprecated models
        self._check_deprecated_models(models)
        # Check the chosen measurements are available for the set collections
        available_measurements = []
        for collection in self._collection_list:
            collection_key = self._available["collections_to_keys"][collection]
            available_measurements.extend(
                self._available["measurements"][collection_key]
            )
        for variable in measurements:
            if variable not in available_measurements:
                raise Exception(
                    "Measurement '{}' not available for collection '{}'. "
                    "Check available with "
                    "SwarmRequest.available_measurements({})".format(
                        variable, collection_key, collection_key
                    )
                )
        # Check if at least one model defined when requesting residuals
        if residuals and not models:
            raise Exception("Residuals requested but no model defined!")
        # Check models format, extract model_ids and string to pass to server
        model_ids, model_expression_string = self._parse_models_input(models)
        # Check chosen aux is available
        for variable in auxiliaries:
            if variable not in self._available["auxiliaries"]:
                raise Exception(
                    "'{}' not available. Check available with "
                    "SwarmRequest.available_auxiliaries()".format(variable)
                )
        # Load the custom .shc file
        if custom_model:
            if os.path.exists(custom_model):
                with open(custom_model) as custom_shc_file:
                    custom_shc = custom_shc_file.read()
                model_ids.append("Custom_Model")
            else:
                raise OSError("Custom model .shc file not found")
        else:
            custom_shc = None

        # Set up the variables that actually get passed to the WPS request

        # Requested variables, start with the measurements ...
        variables = set(measurements)

        # model-related measurements
        _requested_model_variables = [
            variable for variable in measurements if variable in model_variables
        ]

        if residuals:
            # Remove the measurements ...
            variables.difference_update(_requested_model_variables)
            # ... add their residuals instead.
            variables.update(
                f"{variable}_res_{model_id}"
                for variable in _requested_model_variables
                for model_id in model_ids
            )

        else:
            # If no variable is requested fall back to B_NEC.
            if not _requested_model_variables:
                _requested_model_variables = ["B_NEC"]

            # Add calculated model variables.
            variables.update(
                f"{variable}_{model_id}"
                for variable in (
                    model_variables[variable] for variable in _requested_model_variables
                )
                for model_id in model_ids
            )

        # Finally, add the auxiliary variables.
        variables.update(auxiliaries)

        self._request_inputs.model_expression = model_expression_string
        self._request_inputs.variables = list(variables)
        self._request_inputs.sampling_step = sampling_step
        self._request_inputs.custom_shc = custom_shc
        self._request_inputs.ignore_cached_models = ignore_cached_models

        return self

    def set_range_filter(self, parameter, minimum=None, maximum=None, negate=False):
        """Set a range filter to apply.

        Filters data for minimum ≤ parameter ≤ maximum,
        or parameter < minimum OR parameter > maximum if negated.

        Note:
            - Apply multiple filters with successive calls to ``.set_range_filter()``
            - See :py:meth:`SwarmRequest.add_filter` for arbitrary filters.

        Args:
            parameter (str)
            minimum (float or integer)
            maximum (float or integer)

        Examples:
            ``request.set_range_filter("Latitude", 0, 90)``
                to set "Latitude >= 0 AND Latitude <= 90"
            ``request.set_range_filter("Latitude", 0, 90, negate=True)``
                to set "(Latitude < 0 OR Latitude > 90)"
        """
        if not isinstance(parameter, str):
            raise TypeError("parameter must be a str")

        def _generate_filters(minop, maxop):
            if minimum is not None:
                yield f"{parameter} {minop} {minimum}"
            if maximum is not None:
                yield f"{parameter} {maxop} {maximum}"

        nargs = 2 - (minimum is None) - (maximum is None)
        if nargs == 0:
            return

        filter_ = (
            " AND ".join(_generate_filters(">=", "<="))
            if not negate
            else " OR ".join(_generate_filters("<", ">"))
        )

        if nargs > 1:
            filter_ = f"({filter_})"

        self.add_filter(filter_)

        return self

    def set_choice_filter(self, parameter, *values, negate=False):
        """Set a choice filter to apply.

        Filters data for *parameter in values*,
        or *parameter not in values* if negated.

        Note:
            See :py:meth:`SwarmRequest.add_filter` for arbitrary filters.

        Args:
            parameter (str)
            values (float or integer or string)

        Examples:
            ``request.set_choice_filter("Flags_F", 0, 1)``
                to set "(Flags_F == 0 OR Flags_F == 1)"
            ``request.set_choice_filter("Flags_F", 0, 1, negate=True)``
                to set "(Flags_F != 0 AND Flags_F != 1)"
        """
        if not isinstance(parameter, str):
            raise TypeError("parameter must be a str")

        def _generate_filters(compop):
            for value in values:
                yield f"{parameter} {compop} {value!r}"

        nargs = len(values)
        if nargs == 0:
            return

        filter_ = (
            " OR ".join(_generate_filters("=="))
            if not negate
            else " AND ".join(_generate_filters("!="))
        )

        if nargs > 1:
            filter_ = f"({filter_})"

        self.add_filter(filter_)

        return self

    def set_bitmask_filter(self, parameter, selection=0, mask=-1, negate=False):
        """Set a bitmask filter to apply.

        Filters data for *parameter & mask == selection & mask*,
        or *parameter & mask != selection & mask* if negated.

        Note:
            See :py:meth:`SwarmRequest.add_filter` for arbitrary filters.

        Args:
            parameter (str)
            mask (integer)
            selection (integer)

        Examples:
            ``request.set_bitmask_filter("Flags_F", 0, 1)``
                to set "Flags_F & 1 == 0" (i.e. bit 1 is set to 0)
        """
        if not isinstance(parameter, str):
            raise TypeError("parameter must be a str")

        def _get_filter(compop):
            return (
                f"{parameter} & {mask} {compop} {selection & mask}"
                if mask != -1
                else f"{parameter} {compop} {selection}"
            )

        if not negate:
            if mask != 0:  # avoid pointless (0 == 0) filter
                self.add_filter(_get_filter("=="))
        else:
            # mask == 0 leads to (0 != 0) filter and nothing is selected.
            self.add_filter(_get_filter("!="))

        return self

    def add_filter(self, filter_):
        """Add an arbitrary data filter.

        Args:
            filter_ (str): string defining the filter, as shown below

        Filter grammar:

        .. code-block:: text

           filter: predicate
           predicate:
                variable == literal |
                variable != literal |
                variable < number |
                variable > number |
                variable <= number |
                variable >= number |
                variable & unsigned-integer == unsigned-integer |
                variable & unsigned-integer != unsigned-integer |
                (predicate AND predicate [AND predicate ...]) |
                (predicate OR predicate [OR predicate ...]) |
                NOT predicate
           literal: boolean | integer | float | string
           number: integer | float
           variable: identifier | identifier[index]
           index: integer[, integer ...]

           Both single- and double quoted strings are allowed.
           NaN values are matched by the ==/!= operators, i.e., the predicates
           are internally converted to a proper "IS NaN" or "IS NOT NaN"
           comparison.

        Examples:
             "Flags & 128 == 0"
                 Match records with Flag bit 7 set to 0.

             "Elevation >= 15"
                 Match values with values greater than or equal to 15.

             "(Label == "D" OR Label == "N" OR Label = "X")"
                 Match records with Label set to D, N or X.

             "(Type != 1 AND Type != 34) NOT (Type == 1 OR Type == 34)"
                 Exclude records with Type set to 1 or 34.

             "(Vector[2] <= -0.1 OR Vector[2] >= 0.5)"
                 Match records with Vector[2] values outside of the (-0.1, 0.5)
                 range.
        """
        if not isinstance(filter_, str):
            raise TypeError("parameter must be a str")
        self._filterlist.append(filter_)
        # Update the SwarmWPSInputs object
        self._request_inputs.filters = " AND ".join(self._filterlist)

    def clear_filters(self):
        """Remove all applied filters."""
        self._filterlist = []
        self._request_inputs.filters = None
        return self

    clear_range_filter = clear_filters  # alias for backward compatibility

    def applied_filters(self):
        """Print currently applied filters."""
        for filter_ in self._filterlist:
            print(filter_)

    def get_collection_info(self, collections):
        """Get information about a list of collections

        Args:
            collections (list[str]): List of collections to get information for

        Returns:
            list[dict]: A list of dictionaries containing information about each collection

        Examples:

            .. code-block:: python

                from viresclient import SwarmRequest
                request = SwarmRequest("https://vires.services/ows")
                info = request.get_collection_info(["SW_OPER_MAGA_LR_1B"])

            gives::

                [{'name': 'SW_OPER_MAGA_LR_1B',
                'productType': 'SW_MAGx_LR_1B',
                'productCount': 3579,
                'timeExtent': {'start': '2013-11-25T11:02:52Z',
                'end': '2023-09-28T23:59:59Z'}}]
        """
        if not isinstance(collections, list):
            raise TypeError("collections must be a list")
        templatefile = TEMPLATE_FILES["get_collection_info"]
        template = JINJA2_ENVIRONMENT.get_template(templatefile)
        request = template.render(
            collections=",".join(collections),
            response_type="application/json",
        ).encode("UTF-8")
        response = self._get(request, asynchronous=False, show_progress=False)
        response = json.loads(response.decode("UTF-8"))
        return response

    def get_times_for_orbits(
        self, start_orbit, end_orbit, mission="Swarm", spacecraft=None
    ):
        """Translate a pair of orbit numbers to a time interval.

        Args:
            start_orbit (int): a starting orbit number
            end_orbit (int): a later orbit number
            spacecraft (str):
                    Swarm: one of ('A','B','C') or ("Alpha", "Bravo", "Charlie")
                    GRACE: one of ('1','2')
                    GRACE-FO: one of ('1','2')
                    CryoSat-2: None
            mission (str): one of ('Swarm', 'GRACE', 'GRACE-FO', 'CryoSat-2')

        Returns:
            tuple (datetime): (start_time, end_time) The start time of the
            start_orbit and the ending time of the end_orbit.
            (Based on ascending nodes of the orbits)

        """
        # check old function signature and print warning
        if (
            isinstance(start_orbit, str)
            and isinstance(mission, int)
            and spacecraft is None
        ):
            spacecraft, start_orbit, end_orbit = start_orbit, end_orbit, mission
            mission = "Swarm"
            warn(
                "The order of SwarmRequest.get_times_for_orbits() method's "
                "parameters has changed!  "
                "The backward compatibility will be removed in the future.  "
                "Please change your code to:  "
                "request.get_times_for_orbits(start_orbit, end_orbit, "
                "'Swarm', spacecraft)",
                FutureWarning,
            )

        start_orbit = int(start_orbit)
        end_orbit = int(end_orbit)

        # Change to spacecraft = "A" etc. for this request
        spacecraft = self._fix_spacecraft(mission, spacecraft)
        self._check_mission_spacecraft(mission, spacecraft)

        templatefile = TEMPLATE_FILES["times_from_orbits"]
        template = JINJA2_ENVIRONMENT.get_template(templatefile)
        request = template.render(
            mission=mission,
            spacecraft=spacecraft,
            start_orbit=start_orbit,
            end_orbit=end_orbit,
        ).encode("UTF-8")
        response = self._get(request, asynchronous=False, show_progress=False)
        responsedict = json.loads(response.decode("UTF-8"))
        start_time = parse_datetime(responsedict["start_time"])
        end_time = parse_datetime(responsedict["end_time"])
        return start_time, end_time

    def _fix_spacecraft(self, mission, spacecraft):
        # Change to spacecraft = "A" etc. for this request
        spacecraft = str(spacecraft) if spacecraft is not None else None
        if mission == "Swarm" and spacecraft in ("Alpha", "Bravo", "Charlie"):
            spacecraft = spacecraft[0]
        return spacecraft

    def _check_mission_spacecraft(self, mission, spacecraft):
        if mission not in self.MISSION_SPACECRAFTS:
            raise ValueError(
                f"Invalid mission {mission}!"
                f"Allowed options are: {','.join(self.MISSION_SPACECRAFTS)}"
            )

        if self.MISSION_SPACECRAFTS[mission]:
            # missions with required spacecraft id
            if not spacecraft:
                raise ValueError(
                    f"The {mission} spacecraft is required!"
                    f"Allowed options are: {','.join(self.MISSION_SPACECRAFTS[mission])}"
                )
            if spacecraft not in self.MISSION_SPACECRAFTS[mission]:
                raise ValueError(
                    f"Invalid {mission} spacecraft! "
                    f"Allowed options are: {','.join(self.MISSION_SPACECRAFTS[mission])}"
                )

        elif spacecraft:  # mission without spacecraft id
            raise ValueError(
                f"No {mission} spacecraft shall be specified! "
                "Set spacecraft to None."
            )

    def get_orbit_number(self, spacecraft, input_time, mission="Swarm"):
        """Translate a time to an orbit number.

        Args:
            spacecraft (str):
                    Swarm: one of ('A','B','C') or ("Alpha", "Bravo", "Charlie")
                    GRACE: one of ('1','2')
                    GRACE-FO: one of ('1','2')
                    CryoSat-2: None
            input_time (datetime): a point in time
            mission (str): one of ('Swarm', 'GRACE', 'GRACE-FO', 'CryoSat-2')

        Returns:
            int: The current orbit number at the input_time

        """
        try:
            input_time = parse_datetime(input_time)
        except TypeError:
            raise TypeError(
                "input_time must be datetime object or ISO-8601 " "date/time string"
            )
        # Change to spacecraft = "A" etc. for this request
        if spacecraft in ("Alpha", "Bravo", "Charlie"):
            spacecraft = spacecraft[0]
        if mission not in self.MISSION_SPACECRAFTS:
            raise ValueError(
                f"Invalid mission {mission}!"
                f"Allowed options are: {','.join(self.MISSION_SPACECRAFTS)}"
            )
        spacecraft = str(spacecraft)
        if mission == "Swarm":
            collection = f"SW_OPER_MOD{spacecraft}_SC_1B"
        elif mission == "GRACE":
            if spacecraft in "12":
                spacecraft = "AB"[int(spacecraft) - 1]
            elif spacecraft not in "AB":
                raise ValueError(f"Invalid spacecraft: {spacecraft}")
            collection = f"GRACE_{spacecraft}_MAG"
        elif mission == "GRACE-FO":
            collection = f"GF{spacecraft}_OPER_FGM_ACAL_CORR"
        elif mission == "CryoSat-2":
            collection = "CS_OPER_MAG"
        request_inputs = SwarmWPSInputs(
            collection_ids={collection: [collection]},
            begin_time=input_time,
            end_time=input_time + datetime.timedelta(seconds=1),
            variables=["OrbitNumber"],
            response_type="text/csv",
        )
        request = request_inputs.as_xml(self._templatefiles["sync"])
        retdata = ReturnedDataFile(filetype="csv")
        response_handler = self._response_handler(retdata, show_progress=False)
        self._get(
            request,
            asynchronous=False,
            response_handler=response_handler,
            show_progress=False,
        )
        df = retdata.as_dataframe()
        if len(df) == 0:
            raise ValueError(
                "Orbit number not identified. Probably outside of mission duration or orbit counter file."
            )
        elif len(df) > 1:
            raise RuntimeError("Unexpected server response. More than one OrbitNumber.")
        else:
            return df["OrbitNumber"][0]

    def get_model_info(self, models=None, custom_model=None, original_response=False):
        """Get model info from server.

        Handles the same models input as .set_products(), and returns a dict
        like:

        {'IGRF12': {
        'expression': 'IGRF12(max_degree=13,min_degree=0)',
        'validity': {'start': '1900-01-01T00:00:00Z', 'end': '2020-01-01T00:00:00Z'
        }, ...}

        If original_response=True, return the list of dicts like:

        {'expression': 'MCO_SHA_2C(max_degree=16,min_degree=0)',
        'name': 'MCO_SHA_2C',
        'validity': {'start': '2013-11-30T14:38:24Z',
        'end': '2018-01-01T00:00:00Z'}}, ...

        Args:
            models (list/dict): as with set_products
            custom_model (str): as with set_products
            original_response (bool)

        Returns:
            dict or list

        """

        def _request_get_model_info(model_expression=None, custom_shc=None):
            """Make the get_model_info request."""
            templatefile = TEMPLATE_FILES["model_info"]
            template = JINJA2_ENVIRONMENT.get_template(templatefile)
            request = template.render(
                model_expression=model_expression,
                custom_shc=custom_shc,
                response_type="application/json",
            ).encode("UTF-8")
            response = self._get(request, asynchronous=False, show_progress=False)
            response_list = json.loads(response.decode("UTF-8"))
            return response_list

        def _build_dict(response_list):
            """Build dictionary output organised by model name."""
            return {model_dict.pop("name"): model_dict for model_dict in response_list}

        if custom_model:
            with open(custom_model) as custom_shc_file:
                custom_shc = custom_shc_file.read()
            if not models:
                models = ["Custom_Model"]
        else:
            custom_shc = None

        if models is not None:
            _, model_expression = self._parse_models_input(models)
        else:
            model_expression = None

        response = _request_get_model_info(model_expression, custom_shc)

        if not original_response:
            response = _build_dict(response)

        return response

    @staticmethod
    def _check_deprecated_models(models):
        """Print deprecation warning for deprecated models."""
        deprecated_models = []
        for deprecated_model in DEPRECATED_MODELS:
            for model in models:
                if deprecated_model in model:
                    deprecated_models.append(deprecated_model)
                    break
        for deprecated_model in deprecated_models:
            print(
                "WARNING: Model {} is deprecated. {}".format(
                    deprecated_model, DEPRECATED_MODELS[deprecated_model]
                ),
                file=sys.stdout,
            )

    def get_conjunctions(
        self,
        start_time=None,
        end_time=None,
        threshold=1.0,
        spacecraft1="A",
        spacecraft2="B",
        mission1="Swarm",
        mission2="Swarm",
        grade="OPER",
    ):
        """Get times of the spacecraft conjunctions.

        Currently available for the following spacecraft pairs:
          - Swarm-A/Swarm-B

        Args:
            start_time (datetime / ISO_8601 string): optional start time
            end_time (datetime / ISO_8601 string): optional end time
            threshold (float): optional maximum allowed angular separation
                 in degrees; by default set to 1; allowed values are [0, 180]
            spacecraft1: identifier of the first spacecraft, default to 'A'
            spacecraft2: identifier of the second spacecraft, default to 'B'
            mission1 (str): mission of the first spacecraft, defaults to 'Swarm'
            mission2 (str): mission of the first spacecraft, defaults to 'Swarm'
            grade (str): products grade, possible values "OPER" or "FAST"

        Returns:
            ReturnedData:
        """
        try:
            start_time = parse_datetime(start_time) if start_time else None
            end_time = parse_datetime(end_time) if end_time else None
        except TypeError:
            raise TypeError(
                "start_time and end_time must be datetime objects or ISO-8601 "
                "date/time strings"
            ) from None

        if not (0 <= threshold <= 180):
            raise ValueError("Invalid threshold value!")

        spacecraft1 = self._fix_spacecraft(mission1, spacecraft1)
        spacecraft2 = self._fix_spacecraft(mission2, spacecraft2)

        self._check_mission_spacecraft(mission1, spacecraft1)
        self._check_mission_spacecraft(mission2, spacecraft2)

        if (mission1, spacecraft1) == (mission2, spacecraft2):
            raise ValueError("The first and second spacecraft must not be the same!")

        spacecraft_pair = tuple(
            sorted([(mission1, spacecraft1), (mission2, spacecraft2)])
        )

        if spacecraft_pair not in self.CONJUNCTION_MISSION_SPACECRAFT_PAIRS:
            raise ValueError(
                "Conjunctions not available for the requested "
                "spacecraft pair {spacecraft_pair}!"
            )

        templatefile = TEMPLATE_FILES["get_conjunctions"]
        template = JINJA2_ENVIRONMENT.get_template(templatefile)
        request = template.render(
            begin_time=start_time,
            end_time=end_time,
            spacecraft1=spacecraft1,
            spacecraft2=spacecraft2,
            mission1=mission1,
            mission2=mission2,
            grade=(grade if grade and grade != "OPER" else None),
            threshold=threshold,
        ).encode("UTF-8")

        show_progress = False
        leave_progress_bar = False
        response = ReturnedDataFile(filetype="cdf")

        response_handler = self._response_handler(
            retdatafile=response,
            show_progress=show_progress,
            leave_progress_bar=leave_progress_bar,
        )

        self._get(
            request=request,
            asynchronous=False,
            show_progress=show_progress,
            leave_progress_bar=leave_progress_bar,
            response_handler=response_handler,
        )

        return response
