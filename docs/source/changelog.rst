Changelog
=========

* :release:`0.5.1 <2015-11-18>`
* :bug:`-` Reworked the creation of related/auth_model models, order does not matter anymore

* :release:`0.5.0 <2015-10-07>`
* :bug:`- major` Fixed a bug using 'required' '_db_settings' property on 'relationship' field
* :support:`-` Added support for `'nefertari-guards' <https://nefertari-guards.readthedocs.org/>`_
* :support:`-` Added support for Nefertari '_hidden_fields'
* :support:`-` Added support for Nefertari event handlers
* :support:`-` Simplified field processors, '_before_processors' is now called '_processors', removed '_after_processors'
* :support:`-` ACL permission names in RAML now match real permission names instead of http methods
* :support:`-` Added support for the property '_nesting_depth' in schemas

* :release:`0.4.1 <2015-09-02>`
* :bug:`-` Simplified ACLs (refactoring)

* :release:`0.4.0 <2015-08-19>`
* :support:`-` Added support for JSON schema draft 04
* :support:`-` RAML is now parsed using ramlfications instead of pyraml-parser
* :feature:`-` Boolean values in RAML don't have to be strings anymore (previous limitation of pyraml-parser)
* :feature:`-` Renamed setting 'ramses.auth' to 'auth'
* :feature:`-` Renamed setting 'debug' to 'enable_get_tunneling'
* :feature:`-` Field name and request object are now passed to field processors under 'field' and 'request' kwargs respectively
* :feature:`-` Added support for relationship processors and backref relationship processors ('backref_after_validation'/'backref_before_validation')
* :feature:`-` Renamed schema's 'args' property to '_db_settings'
* :feature:`-` Properties 'type' and 'required' are now under '_db_settings'
* :feature:`-` Prefixed all Ramses schema properties by an underscore: '_auth_fields', '_public_fields', '_nested_relationships', '_auth_model', '_db_settings'
* :feature:`-` Error response bodies are now returned as JSON
* :bug:`- major` Fixed processors not applied on fields of type 'list' and type 'dict'
* :bug:`- major` Fixed a limitation preventing collection names to use nouns that do not have plural forms

* :release:`0.3.1 <2015-07-07>`
* :support:`- backported` Added support for callables in 'default' field argument
* :support:`- backported` Added support for 'onupdate' field argument

* :release:`0.3.0 <2015-06-14>`
* :support:`-` Added python3 support

* :release:`0.2.3 <2015-06-05>`
* :bug:`-` Forward compatibility with nefertari releases

* :release:`0.2.2 <2015-06-03>`
* :bug:`-` Fixed password minimum length support by adding before and after validation processors
* :bug:`-` Fixed race condition in Elasticsearch indexing

* :release:`0.2.1 <2015-05-27>`
* :bug:`-` Fixed limiting fields to be searched
* :bug:`-` Fixed login issue
* :bug:`-` Fixed custom processors

* :release:`0.2.0 <2015-05-18>`
* :feature:`-` Added support for securitySchemes, authentication (Pyramid 'auth ticket') and ACLs
* :support:`-` Added several display options to schemas
* :support:`-` Added unit tests
* :support:`-` Improved docs
* :feature:`-` Add support for processors in schema definition
* :feature:`-` Add support for custom auth model
* :support:`-` ES views now read from ES on update/delete_many

* :release:`0.1.1 <2015-04-21>`
* :bug:`-` Ramses could not be used in an existing Pyramid project

* :release:`0.1.0 <2015-04-08>`
* :support:`-` Initial release!
