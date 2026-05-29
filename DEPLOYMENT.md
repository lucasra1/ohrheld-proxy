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

## TLS

The container serves plain HTTP on port `8080`. Terminate TLS at Traefik and route traffic to the Kubernetes service on port `80`.

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

If your GHCR package is private:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=OWNER \
  --docker-password="$GITHUB_TOKEN" \
  --namespace YOUR_NAMESPACE
```

Then add this to `spec.template.spec` in the deployment:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```
