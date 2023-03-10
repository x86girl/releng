# The RDO toolbox

This toolbox contains the tools suite to
build a new RDO release and more.

It's served at https://quay.io/repository/rdoinfra/rdo-toolbox

# How to use it

You must have [toolbox](https://github.com/containers/toolbox) package installed as prerequisite

```
podman pull quay.io/rdoinfra/rdo-toolbox:latest
# or
docker pull quay.io/rdoinfra/rdo-toolbox:latest

toolbox create -i quay.io/rdoinfra/rdo-toolbox:latest
toolbox enter rdo-toolbox-latest
```

# How to build it locally
```
podman build -f Containerfile -t rdo-toolbox:local
toolbox create -i localhost/rdo-toolbox:local
toolbox enter rdo-toolbox-local
```
