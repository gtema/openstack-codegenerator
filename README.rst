=======================
OpenStack CodeGenerator
=======================

Primary goal of the project is to simplify maintainers life by generating
complete or at least parts of the code.

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
