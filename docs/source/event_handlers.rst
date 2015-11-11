Event Handlers
==============

Ramses supports `Nefertari event handlers <http://nefertari.readthedocs.org/en/stable/event_handlers.html>`_. Ramses event handlers also have access to `Nefertari's wrapper API <http://nefertari.readthedocs.org/en/stable/models.html#wrapper-api>`_ which provides additional helpers.


Setup
-----


Writing Event Handlers
^^^^^^^^^^^^^^^^^^^^^^

You can write custom functions inside your ``__init__.py`` file, then add the ``@registry.add`` decorator before the functions that you'd like to turn into CRUD event handlers. Ramses CRUD event handlers has the same API as Nefertari CRUD event handlers. Check Nefertari CRUD Events doc for more details on events API.

Example:

.. code-block:: python


    import logging
    from ramses import registry


    log = logging.getLogger('foo')

    @registry.add
    def log_changed_fields(event):
        changed = ['{}: {}'.format(name, field.new_value)
                   for name, field in event.fields.items()]
        logger.debug('Changed fields: ' + ', '.join(changed))


Connecting Event Handlers
^^^^^^^^^^^^^^^^^^^^^^^^^

When you define event handlers in your ``__init__.py`` as described above, you can apply them on per-model basis. If multiple handlers are listed, they are executed in the order in which they are listed. Handlers should be defined in the root of JSON schema using ``_event_handlers`` property. This property is an object, keys of which are called "event tags" and values are lists of handler names. Event tags are composed of two parts: ``<type>_<action>`` whereby:

**type**
    Is either ``before`` or ``after``, depending on when handler should run - before view method call or after respectively. You can read more about when to use `before vs after event handlers <http://nefertari.readthedocs.org/en/stable/event_handlers.html#before-vs-after>`_.

**action**
    Exact name of Nefertari view method that processes the request (action) and special names for authentication actions.

Complete list of actions:
    * **index** - Collection GET
    * **create** - Collection POST
    * **update_many** - Collection PATCH/PUT
    * **delete_many** - Collection DELETE
    * **collection_options** - Collection OPTIONS
    * **show** - Item GET
    * **update** - Item PATCH
    * **replace** - Item PUT
    * **delete** - Item DELETE
    * **item_options** - Item OPTIONS
    * **login** - User login (POST /auth/login)
    * **logout** - User logout (POST /auth/logout)
    * **register** - User register (POST /auth/register)
    * **set** - triggers on all the following actions: **create**, **update**, **replace**, **update_many** and **register**.


Example
-------

We will use the following handler to demonstrate how to connect handlers to events. This handler logs ``request`` to the console.

.. code-block:: python

    import logging
    from ramses import registry


    log = logging.getLogger('foo')

    @registry.add
    def log_request(event):
        log.debug(event.view.request)


Assuming we had a JSON schema representing the model ``User`` and we want to log all collection GET requests on the ``User`` model after they are processed using the ``log_request`` handler, we would register the handler in the JSON schema like this:

.. code-block:: json

    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "_event_handlers": {
            "after_index": ["log_request"]
        },
        ...
    }


Other Things You Can Do
-----------------------

You can update another field's value, for example, increment a counter:

.. code-block:: python

    from ramses import registry


    @registry.add
    def increment_count(event):
        instance = event.instance or event.response
        counter = instance.counter
        incremented = counter + 1
        event.set_field_value('counter', incremented)


You can update other collections (or filtered collections), for example, mark sub-tasks as completed whenever a task is completed:

.. code-block:: python

    from ramses import registry
    from nefertari import engine

    @registry.add
    def mark_subtasks_completed(event):
        if 'task' not in event.fields:
            return

        completed = event.fields['task'].new_value
        instance = event.instance or event.response

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            subtasks = subtask_model.get_collection(task_id=instance.id)
            subtask_model._update_many(subtasks, {'completed': True})


You can perform more complex queries using Elasticsearch:

.. code-block:: python

    from ramses import registry
    from nefertari import engine
    from nefertari.elasticsearch import ES


    @registry.add
    def mark_subtasks_after_2015_completed(event):
        if 'task' not in event.fields:
            return

        completed = event.fields['task'].new_value
        instance = event.instance or event.response

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            es_query = 'task_id:{} AND created_at:[2015 TO *]'.format(instance.id)
            subtasks_es = ES(subtask_model.__name__).get_collection(_raw_terms=es_query)
            subtasks_db = subtask_model.filter_objects(subtasks_es)
            subtask_model._update_many(subtasks_db, {'completed': True})
