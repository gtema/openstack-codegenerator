OpenApi Schema
==============

CodeGenerator is able to generate OpenAPI specs for certain services by
inspecting their code. This requires service package being installed in the
environment where the generator is running. It then tries to initialize service
application and for supported runtimes scans for the exposed operations. At the
moment following services are covered:

- Nova

- Neutron

- Cinder

- Glance

- Keystone

- Octavia


Generator can be invoked after installing it as a regular python project with
dependencies

.. code-block:: console

  openstack-codegenerator --target openapi-spec --work-dir wrk --service-type compute

The generator is having possibility to additionally parse rendered service
API-REF HTML documentation and supplement descriptions in the generated
OpenApi spec by trying to find corresponding information in the html.

.. code-block:: console

  openstack-codegenerator --target openapi-spec --work-dir wrk --service-type compute --api-ref-src <PATH_TO_RENDERED_DOC>.html


Another project for rendering generated OpenAPI specs in the style
similar (but not the same way) to currently used os-api-ref:
`https://github.com/gtema/openstack-openapi`. It implements a
Sphinx extension that reads spec file and converts it to internal
sphinx directives to get a proper structure in the rendered HTML
and styles it using `BootstrapV5` library. Sample rendering can be
seen under `https://gtema.github.io/openstack-openapi/`


Highlevel description (for contributor)
---------------------------------------

Base generator
:class:`~codegenerator.openapi.base.OpenStackServerSourceGenerator` is
supporting WSGI + Routes based application out of box. For such applications
it tries to get the main router from wich all exposed routes are being
analysed. During routes processing generator is searching for supported
decorators and frameworks in order to extract as most information about the
operation as possible:

- url
- method
- path parameters
- query parameters
- expected body jsonschema
- response jsonschema
- expected response and error codes
- operation description (docstrings)

Generator for every covered OpenStack service is inherits from the Base
generator (i.e. :class:`~codegenerator.openapi.nova.NovaGenerator`. It is
expected that `init` method will perform service setup activities (i.e.
database creation or config file preparation whenever required) and sets the
main application router. `generate` method of the class is then being invoked
and it reads current spec file (if present to update it) and loops over all
exposed routes. For each route a dedicated method `_process_route` is
invoked, which in turn invoke multiple additional methods for parameters or
body schemas processing.

After processing when api-ref html is available a dedicated method
:class:`~codegenerator.openapi.utils.merge_api_ref_doc` can be called to add
available descriptions (operation, parameters).

.. note::
   Since all services use `oslo_config` and `oslo_policy` libraries which rely
   on global state they race with each other. In order to avoid this processing
   rely on multiprocessing to isolate services.


Nova
----

Source code of Nova currently provides full information about exposed routes
and query/path parameters, as well as jsonschema of request body. Sadly it does
not contain jsonschemas of the responses. CodeGenerator at the moment covers
those missing schemas directly in the code and injects them into the schema via
:class:`~codegenerator.openapi.nova.NovaGenerator:_get_schema_ref`

After stabilization it is expected to move implemented schemas into the Nova
source code base.


Cinder
-------

Cinder is very similar to Nova so everything mentioned above is applicable
here as well.

for Cinder at the moment all operations are duplicated under
`v3/${project_id}/...` and `v3/...`. For the sake of standartization
project_id urls are excluded from the produces spec file.


Glance
------

Glance is also using `routes` for exposing application. However in difference
to Nova and Cinder it does not describe request parameters of bodies in an
expected way. Current implementation of the Glance generator therefore is
looking at the request serializer and deserializer attached to the operation
controllers. When this information is present and contain usable jsonschema
it is being used. In other cases similar approach to Nova with hardcoding
response information is being used. But since Glance code base contain
certain useful jsonschemas (not connected in the routes) generator gets those
schemas directly from the code (where the mapping is known).


Keystone
--------

This service is using `Flask` framework which gives similar capabilities to
the `routes`. However here there are no body information at all (neither
Request nor Response). Also here there are certain jsonschemas found directly
in the Keystone code base and connected for the schema generation.


Neutron
-------

This is where things are getting more challenging.

Neutron requires having DB provisioned and an in-memory DB seems not to be
possible due to technics for the DB communication. In addition to that config
file enabling desired extensions is expected. All this activities are covered
in :class:`~codegenrator.openapi.neutron.NeutronGenerator:setup_neutron`.
According to the current information it is not possible to have all possible
Neutron extensions and plugins enabled at the same time. This is solved by
generator spinning multiple subprocesses that bootstrap Neutron with different
configuration and then merge results. This is handled by spinning up Neutron
few times with independent configurations and merging resulting spec.

Additional challenge in Neutron is that it does not use `routes` to expose
operations directly, but is having a mix of `routes` based operations for
extensions and `pecan` app for the base functionality. Since the `pecan`
framework is based on a purely dynamic routing there is no possibility to
extract information about exposed routes by doing code inspection. Luckily only
base operations (router/net/subnet) are implemented this way. Therefore
generator registers known `pecan` operations into the extensions router and
normal generator flow is being invoked.

Next challenge is that for Neutron there is no description of bodies at all,
but certain controllers are having `API_DEFINITION` attached. While this is not
a jsonschema at all it can be used to create one where possible. Sadly there is
still sometime no possibility to properly estimate whether certain operation is
exposed and functioning or it is exposed but fails permanently due to the fact,
that `API_DEFINITION` extrapolation fails for this operation.
:class:`~codegenerator.openapi.neutron.get_schema` method is responsible for
conversion of the `API_DEFINITION` into the jsonschema, but is not able to work
perfectly until additional work is invested.

Certain additional operations (addRouterInterface, addExtraRoute, ...) are not
having any information available and require to be also hardcodede in the
generator.


Octavia
-------

Octavia is also based on the `pecan` with its dynamic routing, but the
majority of controllers are available for scanning due to the source code
classes hierarchy. To keep the generation process close to generics
:class:`~codegenerator.openapi.octavia.OctaviaGenerator` is constructing
`routes` router from this information and adds few known exceptions. For the
produced routing table generic process is being invoked which is then looking
at the `WSME` decorators attached to the exposed operations. Since `WSME`
schema is not a jsonschema on its own but it can be considered as an
alternative to jsonschema a naive conversion is implemented in
:class:`~codegenerator.openapi.base._convert_wsme_to_jsonschema`.
