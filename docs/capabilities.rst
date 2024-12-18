VirES capabilities
==================

VirES provides more than just *access* to data. Some operations can be peformed on the data in-situ on the server side before being delivered to you.

.. tabs::

  .. group-tab:: Swarm

    **Data subsetting/filtering**
      | Select data satisfying given conditions (e.g. searching a geographical range; selecting by quality flags)
      | :py:meth:`viresclient.SwarmRequest.set_range_filter`
      | :py:meth:`viresclient.SwarmRequest.set_choice_filter`
      | :py:meth:`viresclient.SwarmRequest.set_bitmask_filter`
      | :py:meth:`viresclient.SwarmRequest.add_filter` (for arbitrary filters)
    **Data resampling**
      | Time series can be resampled to a given cadence
      | See `sampling_step` option in :py:meth:`viresclient.SwarmRequest.set_products`
    **Querying information about data**
      | *For example:*
      | :py:meth:`viresclient.SwarmRequest.available_times`
      | :py:meth:`viresclient.SwarmRequest.get_orbit_number`
      | :py:meth:`viresclient.SwarmRequest.get_times_for_orbits`
      | :py:meth:`viresclient.SwarmRequest.get_collection_info`
    **Geomagnetic model evaluation**
      | Forwards evaluation of magnetic field models when a magnetic dataset is selected (e.g. ``MAGx_LR``). For more detail, see :ref:`Geomagnetic model handling`.
      | :py:meth:`viresclient.SwarmRequest.available_models`
      | :py:meth:`viresclient.SwarmRequest.get_model_info`
      | `models` option in :py:meth:`viresclient.SwarmRequest.set_products`
    **Identifying conjunctions between spacecraft**
      | :py:meth:`viresclient.SwarmRequest.get_conjunctions`
    **Synchronous and asynchronous processing**
      When using :py:meth:`viresclient.SwarmRequest.get_between` with small requests, change the default of `asynchronous=True` to `asynchronous=False` to process faster (no progress bar). By default, jobs are processed asynchronously (i.e. entered into a queue) which is appropriate for longer requests. You can only have two asynchronous jobs running at one time.

  .. group-tab:: Aeolus

    **Data subsetting/filtering**
      | Select data satisfying given conditions (e.g. searching a geographical range; selecting by quality flags)
      | :py:meth:`viresclient.AeolusRequest.set_range_filter`
      | :py:meth:`viresclient.AeolusRequest.set_bbox`
    **Querying information about data**
      | *For example:*
      | :py:meth:`viresclient.AeolusRequest.available_times`
    **Synchronous and asynchronous processing**
      When using :py:meth:`viresclient.AeolusRequest.get_between` with small requests, change the default of `asynchronous=True` to `asynchronous=False` to process faster (no progress bar). By default, jobs are processed asynchronously (i.e. entered into a queue) which is appropriate for longer requests. You can only have two asynchronous jobs running at one time.

**Uploading data**
  | Data of certain formats can be uploaded to the server and then manipulated like existing datasets (available privately within your account)
  | See :doc:`cli` and :py:meth:`viresclient.DataUpload`
