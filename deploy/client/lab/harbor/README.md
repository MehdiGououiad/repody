# Harbor — OpenShift client lab (Docker Compose)

Harbor runs **on the host** via the [official Docker Compose installer](https://goharbor.io/docs/main/install-config/run-installer-script/), not inside the OpenShift cluster.

## Start

```powershell
pnpm openshift:harbor
# or as part of infra:
pnpm openshift:infra
```

Defaults:

| Setting | Value |
|---------|--------|
| UI / push | `http://localhost:5080` |
| Admin | `admin` / `Harbor12345` |
| Project | `repody` |
| Push registry | `localhost:5080/repody` |

## CRC pulls from host Harbor

OpenShift pods cannot use `localhost`. Set the cluster-visible host before `push` / `seed`:

```powershell
$env:REPODY_HARBOR_CLUSTER_HOST="host.crc.internal:5080"
```

You may also need to allow the insecure registry on CRC (lab only) — see [OpenShift registry sources](https://docs.openshift.com/container_platform/latest/openshift_images/image-configuration.html).

Config template: [harbor.yml](./harbor.yml) (copied into `.runtime/harbor-installer-*` by the script).
