Field Processors
================

Writing Processors
------------------

You can write custom functions inside your ``__init__.py`` file, then simply add the ``@registry.add`` decorator before the functions that you'd like to turn into processors. A processor receives two arguments: `instance`, the object instance being created or updated, and `new_value`, the new value being set.

.. code-block:: python

    @registry.add
    def processor(instance, new_value):
        """ This is a field processor """
        return new_value


Things You Can Do
-----------------

You can update another field's value.

.. code-block:: python

    @registry.add
    def processor(instance, new_value):
        """ Update other_field """
        instance.other_field = "other_value"

        return new_value


You can transform the value of a field, for example crypt a password before saving it.

.. code-block:: python

    @registry.add
    def processor(instance, new_value):
        """ Crypt new_value if it's not crypted yet """
        import cryptacular.bcrypt
        crypt = cryptacular.bcrypt.BCRYPTPasswordManager()

        if new_value and not crypt.match(new_value):
            new_value = str(crypt.encode(new_value))

        return new_value


You can update other collections or other filtered collections whenever the field is being updated to a certain value.

.. code-block:: python

    @registry.add
    def processor(instance, new_value):
        """ Update 5 latest OtherModel that have foo=bar """
        from nefertari import engine

        _other_model = engine.get_document_cls("OtherModel")
        objects = _other_model.get_collection(foo=bar, _sort="created_at", _limit=5)
        _other_model._update_many(objects, {"bar": "foo"})

        return new_value

