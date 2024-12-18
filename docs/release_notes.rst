Release notes
=============

Change log
----------

Changes from 0.11.8 to 0.12.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added TOLEOS thermosphere products:

  - e.g. ``"CH_OPER_DNS_ACC_2_"`` and ``"CH_OPER_WND_ACC_2_"`` from CHAMP and equivalents from GRACE and GRACE-FO
  - conjunction information within ``"MM_CON_SPH_2_:crossover"`` and ``"MM_CON_SPH_2_:plane_alignment"``

- Added CHAMP magnetic dataset, ``CH_ME_MAG_LR_3``
- Added :py:meth:`viresclient.SwarmRequest.get_collection_info`

Changes from 0.11.7 to 0.11.8
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added FAC FAST dataset ``SW_FAST_FACxTMS_2F``

Changes from 0.11.6 to 0.11.7
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added auxiliaries ``["F107_avg81d", "F107_avg81d_count"]``
- Updated and added ML-calibrated variants of GOCE & GRACE-FO magnetic datasets, ``GO_MAG_ACAL_CORR_ML`` & ``GFx_MAG_ACAL_CORR_ML``

Changes from 0.11.5 to 0.11.6
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix to allow multiple VOBS to be fetched in one request

Changes from 0.11.4 to 0.11.5
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix :py:meth:`viresclient.SwarmRequest.available_times` usage with pandas 2.x

Changes from 0.11.3 to 0.11.4
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Support for (L1B) FAST data

Changes from 0.11.2 to 0.11.3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added ``ignore_cached_models=True`` in :py:meth:`viresclient.SwarmRequest.set_products`
- Added description of model handling in docs

Changes from 0.11.1 to 0.11.2
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix support for cdflib version 1.0

Changes from 0.11.0 to 0.11.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``viresclient`` package now available through conda-forge
- Added parameter to Swarm ``MAG`` collections: ``dF_Sun``
- Added GOCE ML magnetic dataset: ``GO_MAG_ACAL_CORR_ML``

Changes from 0.10.3 to 0.11.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Breaking change:**

  - :py:meth:`viresclient.ReturnedData` property ``.range_filters`` changed to ``.data_filters``
  - Xarray datasets attributes (``.attrs`` property) have ``"RangeFilters"`` changed to ``"AppliedFilters"``

- Added new arbitrary data filter functionality, with new methods:

  - :py:meth:`viresclient.SwarmRequest.set_range_filter`
  - :py:meth:`viresclient.SwarmRequest.set_choice_filter`
  - :py:meth:`viresclient.SwarmRequest.set_bitmask_filter`
  - :py:meth:`viresclient.SwarmRequest.add_filter`

- Added new collections for Swarm:

  - ``SW_PREL_EFIxIDM_2_`` (type ``EFI_IDM``: ion drift velocities & effective masses, SLIDEM project)
  - ``GO_MAG_ACAL_CORR`` (type ``MAG_GOCE``: magnetic data from the GOCE mission)

- Added new collections for Aeolus:

  - ``ALD_U_N_1A``

- Fixed bug in merging multi-file datasets when loading as xarray

Changes from 0.10.2 to 0.10.3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added new collections:

  - ``SW_OPER_EFIxTIE_2_`` (type ``EFI_TIE``: ion temperatrues)
  - ``SW_EXPT_EFIx_TCT02`` & ``SW_EXPT_EFIx_TCT16`` (types ``EFI_TCT02``, ``EFI_TCT16``: cross-track ion flows)

Changes from 0.10.1 to 0.10.2
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Removed upper version limits for dependencies

Changes from 0.10.0 to 0.10.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Update Jinja2 dependency

Changes from 0.9.1 to 0.10.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added functionality to support VirES for Aeolus. See https://notebooks.aeolus.services
- Added dependency: `netCDF4 <https://github.com/Unidata/netcdf4-python>`_

Changes from 0.9.0 to 0.9.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added :py:meth:`viresclient.SwarmRequest.get_conjunctions` to fetch Swarm A/B conjunctions
- Fixed compatibility with xarray v0.19 of ``reshape`` kwarg in :py:meth:`viresclient.ReturnedData.as_xarray`

Changes from 0.8.0 to 0.9.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added support for:

  - PRISM products (``SW_OPER_MITx_LP_2F``, ``SW_OPER_MITxTEC_2F``, ``SW_OPER_PPIxFAC_2F``)
  - Multi-mission magnetic products (``CS_OPER_MAG``, ``GRACE_x_MAG``, ``GFx_OPER_FGM_ACAL_CORR``)
  - Swarm spacecraft positions (``SW_OPER_MODx_SC_1B``)

- Fixed missing auxiliary "dDst"
- Fixed fetching longer time series of hourly observatory products
- Added new progress bar that tracks processing of chunks in long requests

Changes from 0.7.2 to 0.8.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added support for:

  - VOBS products (Virtual Observatories), e.g. collection ``SW_OPER_VOBS_1M_2_``
  - AUX_OBSH products (hourly ground observatory data)

- Added :py:meth:`viresclient.SwarmRequest.available_times` to query temporal availability of any collection
- Added new ``reshape=True`` kwarg to :py:meth:`viresclient.ReturnedData.as_xarray` to enable optional reshaping of xarray datasets loaded from VOBS and AUX_OBS collections to higher-dimensional objects containing a new dimension (``IAGA_code`` for AUX_OBS and ``SiteCode`` for VOBS)
- Added command line tool, ``viresclient clear_credentials``, to help delete the stored credentials
- Changed tqdm progress bars to use ``tqdm.notebook`` when in Jupyter notebook (otherwise still uses plain tqdm)
- Dropped ``"Timestamp"`` variable attribute ``"units"`` (i.e. ``ds["Timestamp"].attrs["units"]``) when loading as ``xarray.Dataset``, for compatibility with xarray 0.17 when saving as netcdf

Changes from 0.7.1 to 0.7.2
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix usage of cdflib v0.3.20

Changes from 0.7.0 to 0.7.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix use of ``expand`` in ``.as_dataframe()`` for ``AUX_OBS``

Changes from 0.6.2 to 0.7.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added support for:

  - AUX_OBS products
  - AEBS products
  - MLI_SHA_2E

- See :ref:`Available parameters for Swarm` for details of the collection and measurement names
- Added :py:meth:`viresclient.SwarmRequest.available_observatories` to query the AUX_OBS collections to identify IAGA codes available within each collection

Changes from 0.6.1 to 0.6.2
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added automatic initialisation of access token when running on VRE
- Added new composed model aliases (shortcuts)

Changes from 0.6.0 to 0.6.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fix to support the new EEFxTMS_2F baseline 02:

  - Product now available for Swarm Charlie (``C``)
  - ``EEF`` unit changed from ``V/m`` to ``mV/m``
  - New measurement, ``EEJ``
  - Variable renamed: ``flag`` to ``Flag``

Changes from 0.5.0 to 0.6.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Provides access to ``MAGx_HR`` collections (50Hz magnetic measurements)
- Allows pandas v1.0+
- Dataframe index name is now set to "Timestamp" (fixes regression in a previous version)

Changes from 0.4.3 to 0.5.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- IGRF model series have changed name: ``IGRF-12`` is dropped in favour of ``IGRF`` which now provides the latest IGRF (currently IGRF-13)
- ``request.available_collections("MAG")`` can now be called to filter by collection groups, *and now returns a dict instead of a list*
- Improvements for ``xarray.Dataset`` support:

  - NEC now provided as named coordinates for ``B_NEC``-type variables
  - Similarly (VFM, quaternion, WGS84) coordinates also provided for the variables ["B_VFM", "dB_Sun", "dB_AOCS", "dB_other", "B_error"], ["q_NEC_CRF"], ["GPS_Position", "LEO_Position"] respectively
  - Metadata (units and description) are now set for each variable
  - (With xarray 0.14+, try ``xarray.set_options(display_style="html")`` for nicer output)

Changes from 0.4.2 to 0.4.3
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- AMPS is now accessible as a regular model on the DISC server, see::

    request = SwarmRequest("https://staging.viresdisc.vires.services/ows")
    request.get_model_info(["AMPS"])

- xarray.Dataset objects now contain dimension names for all variables. Variables containing ``B_NEC`` get the ``NEC`` dimension name.
- CHAOS model series have changed name: ``CHAOS-6-Core`` etc. is dropped for ``CHAOS-Core`` etc. which provides the latest version of the CHAOS models (currently CHAOS-7)
- Better error message when authentication with server fails.
- When in notebooks: Detect empty or invalid credentials (e.g. on first usage), direct user to the token generation page, and prompt for token input.
- Added ``request.list_jobs()`` to give info on previous two jobs on the server (failed/running/succeeded).

Changes from 0.4.1 to 0.4.2
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed orbit number queries (get_orbit_number)
- Added model sources to model info

Changes from 0.4.0 to 0.4.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added low level data upload API and CLI
- Added set_token convenience function for quick configuration
- Changed list of accessible models:

  - Removed ``MCO_SHA_2F``, ``SIFM``
  - Added ``MF7``, ``LCS-1``

Changes from 0.3.0 to 0.4.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed issues with running on Windows
- Enforcing Python v3.5+ for installation
- Allowing higher versions of cdflib, pandas, and xarray
- Added CLI configuration for setting server address and token
- Metadata for source lineage is now easier to access (names of original ESA data files, details of models used, and filters applied). These are set as properties of :meth:`viresclient.ReturnedData` (i.e. ``data``) and as metadata (``.attrs``) in the ``Dataset`` returned from ``.as_xarray()``::

    data.sources
    data.magnetic_models
    data.range_filters

    ds = data.as_xarray()
    ds.Sources
    ds.MagneticModels
    ds.RangeFilters

- Added access to collections ``SW_OPER_IPDxIRR_2F``
- Added auxiliary data ``F107`` which is the hourly F10.7 value. This is in addition to ``F10_INDEX`` which was already present, which is a daily average.
- Added possibility of accessing multiple collections simultaneously, e.g.::

    request.set_collection("SW_OPER_MAGA_LR_1B", "SW_OPER_MAGC_LR_1B")

- Added optional "expansion" of dataframes with::

    data.as_dataframe(expand=True)

  This expands columns which contain vectors (e.g. ``B_NEC``) into separate columns named like: ``B_NEC_N``, ``B_NEC_E``, ``B_NEC_C``. This is recommended so that numpy operations will work on the columns. The default is ``expand=False`` to preserve the older behaviour.

Changes from v0.2.6 to 0.3.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^-

- Service officially open to public through self-registration on https://vires.services
- Token-based authentication added

Changes from v0.2.5 to 0.2.6
^^^^^^^^^^^^^^^^^^^^^^^^^^^-

- New model composition behaviour is implemented, extending what is possible with the ``models`` kwarg in :meth:`viresclient.SwarmRequest.set_products` (with backwards compatibility). See demo in https://github.com/smithara/viresclient_examples/blob/master/model_residuals_and_cartopy.ipynb
- New method :meth:`viresclient.SwarmRequest.get_model_info` to fetch model details from server.
- :meth:`viresclient.SwarmRequest.available_models` is updated with these details.
- New parameters in TEC collections: ``Elevation_Angle``, ``Absolute_VTEC``.
- New parameters in auxiliaries: ``OrbitDirection``, ``QDOrbitDirection``.
- The auxiliary ``Kp`` is now provided as the proper Kp value, and ``Kp10`` is provided with the old behaviour with the value of Kp*10.
- Updated dependency on cdflib to v0.3.9, and xarray to allow both v0.10.x and v0.11.x.

Changes from v0.2.4 to 0.2.5
^^^^^^^^^^^^^^^^^^^^^^^^^^^-

- EFI collections have changed from ``SW_OPER_EFIx_PL_1B`` to ``SW_OPER_EFIx_LP_1B``, with different measurement variables
- Added support for user-defined models by providing a .shc file path as the ``custom_model`` in :meth:`viresclient.SwarmRequest.set_products`. Model evaluations and residuals will then be returned, named as "Custom_Model", in the same way as other models behave.
- Added alternative input start and end times as ISO-8601 strings to :meth:`viresclient.SwarmRequest.get_between`
- Minor bug fixes

Changes from v0.2.1 to v0.2.4
^^^^^^^^^^^^^^^^^^^^^^^^^^^--

- Added models CHAOS-6-MMA-Primary and CHAOS-6-MMA-Secondary

Changes from v0.2.0 to v0.2.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^--

 - Improved performance of pandas and xarray loading from cdf.
 - Added ``nrecords_limit`` option to :meth:`viresclient.SwarmRequest.get_between` to override the default maximum number of records in each request. Use this if a request is failing with a server error that the maximum allowable number of records has been exceeded - but this means that there is probably duplicate data on the server (old and new versions), so check the data that gets returned::

    data = request.get_between(start_time, end_time, nrecords_limit=3456000)
    ds = data.as_xarray()
    # Identify negative time jumps
    np.where(np.diff(ds["Timestamp"]).astype(float) < 0)
    # e.g [2519945, 5284745, 5481414]
    for i in [2519945, 5284745, 5481414]:
        print(ds.isel(Timestamp=i))
    # Length of day should be 86400
    ds.sel(Timestamp='2014-02-02')

 - Added ``tmpdir`` option to :meth:`viresclient.SwarmRequest.get_between` to override the default temporary file directory. The default is selected automatically according to https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp (usually /tmp). This may not be suitable when fetching large amounts of data as some machines may have limited space available in /tmp or there may be a higher performance or preferred location.

Changes from v0.1.0 to v0.2.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^--

 - Now use ``SwarmRequest`` instead of ``ClientRequest``.
 - kwarg ``subsample`` changed to ``sampling_step``.
 - Added references to .available_collections() and .available_models().
 - User credentials are automatically stored in a configuration file ``~/.viresclient.ini``.
 - Downloads are streamed to temporary files instead of being held in memory.
 - Any size request is now supported. Large requests are automatically chunked up.
 - Added download progress bar indicating size in MB.
 - xarray added as a dependency and ``.as_xarray()`` method added.
