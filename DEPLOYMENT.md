# Deploying the HTTP Proxy

You do not strictly need a new GitHub repo. You need:

1. A GitHub repository that can hold this source code and publish a GHCR image.
2. A Git repository that Argo CD watches for Kubernetes manifests.

Those can be the same repository, or you can use your existing GitOps repository for `k8s/`.

## Build and Push to GHCR From Your Laptop

Replace `OWNER` with your GitHub org/user.

```bash
export GHCR_IMAGE=ghcr.io/OWNER/hearables-proxy:0.1.0

docker build -t "$GHCR_IMAGE" .
echo "$GITHUB_TOKEN" | docker login ghcr.io -u OWNER --password-stdin
docker push "$GHCR_IMAGE"
```

Your GitHub token needs `write:packages` to push the image. If the package is private, your cluster also needs pull credentials.

If the pod fails with `exec /usr/local/bin/python: exec format error`, the image was built for a different CPU architecture than the Kubernetes node. This commonly happens when building on Apple Silicon and deploying to `amd64` Linux nodes.

Build and push an `amd64` image instead:

```bash
export GHCR_IMAGE=ghcr.io/OWNER/hearables-proxy:0.1.0

docker buildx build \
  --platform linux/amd64 \
  -t "$GHCR_IMAGE" \
  --push \
  .
```

Or publish a multi-architecture image:

```bash
export GHCR_IMAGE=ghcr.io/OWNER/hearables-proxy:0.1.0

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t "$GHCR_IMAGE" \
  --push \
  .
```

## TLS

The container serves plain HTTP on port `8080`. Traefik terminates TLS for `ohrheld-proxy.base3.at` and routes traffic to the Kubernetes service on port `80`.

The included Ingress uses:

```yaml
cert-manager.io/cluster-issuer: default
```

If your cluster uses a namespaced cert-manager `Issuer` instead of a `ClusterIssuer`, change that annotation to:

```yaml
cert-manager.io/issuer: default
```

## Point the Manifests at Your Image

Edit `k8s/base/deployment.yaml`:

```yaml
image: ghcr.io/OWNER/hearables-proxy:0.1.0
```

Commit and push the manifests to the repository Argo CD watches.

## Argo CD

Create an Argo CD app that points at this path:

```text
k8s/base
```

If you already have an Argo CD GitOps repo, copy `k8s/base` there instead of creating a separate application repo.

## Image Pull Secrets for Private GHCR Packages

If your GHCR package is private, this base includes an `InfisicalSecret` that creates a Docker config secret named `ghcr-secret` from Infisical path `/github-container-registry`.

The deployment uses that generated secret as its image pull secret:

```yaml
imagePullSecrets:
  - name: ghcr-secret
```
