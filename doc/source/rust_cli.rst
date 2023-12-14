OSC in Rust
===========

A new experimental CLI is generated from the OpenAPI
specs. Due to the fact that it is fully automatically
generated it differs from the current OpenStackClient in
following aspects:

- enforced naming convention
- similar UX for all services
- improved performance
- improved UX
- ...


Currently the generated code is hosted under
`https://github.com/gtema/openstack` It covers all
services for which OpenAPI specs exist with version
dicovery and partial microversion negotiation.


TODO
