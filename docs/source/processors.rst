Field Processors
================

Writing Processors
------------------

You can then define each custom processor in a function in your ``__init__.py`` file. A processor receives two arguments: `instance`, the object's instance, and `new_value`, the new value being set.

.. code-block:: python

    @registry.add
    def custom_processor(instance, new_value):
        """ This is a field processor """
        return (new_value or '').lower().strip()


Accessing Other Models
----------------------

