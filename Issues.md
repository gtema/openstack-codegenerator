# CodeGeneration issues

- strongly typed languages require to know whether resource field is mandatory
  or optional not only in request, but also in response
- fields with microversion restrictions require becoming either optional or we
  have to have microversion specific types (this seems to be the way)
- microversion specific types on the CLI are not intuitive to the user (make
  further wrappers around the CLI harder)
- a way of specifying whether field should be presented in the list (or list -o
  wide) need to be found.
- stricter fields types must be defined (especially python int vs u8, i32, etc)


## Neutron

- need to find maximum possible configuration
- from api_def it is not always clear whether specific resource operation is
  available. I.e. auto-allocated-topology api-def specifies all attributes
  allow-post: False, but the controller is still exposed
  : method: POST, uri: http://192.168.122.63:9696/networking/v2.0/auto-allocated-topology/906e1808a0ca4aeeb3680be889db0625 returns 400
- POST call to /availability_zones is possible, but return 400
