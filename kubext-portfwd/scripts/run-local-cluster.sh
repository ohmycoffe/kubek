#!/usr/bin/env bash

set -eEuox pipefail

CLUSTER_NAME="kubepf-test"
MANIFEST="$(dirname "$0")/../tests/resources/k8s/local-cluster.yaml"
NAMESPACE="demo"

require() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "$1 is required"
        exit 1
    }
}

require kind
require kubectl

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "Deleting existing cluster..."
    kind delete cluster --name "${CLUSTER_NAME}"
fi

echo "Creating cluster..."
kind create cluster --name "${CLUSTER_NAME}"

kubectl config use-context "kind-${CLUSTER_NAME}"

echo "Waiting for nodes..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

echo "Creating namespace..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "Applying manifests..."
kubectl apply -n "${NAMESPACE}" -f "${MANIFEST}"

echo "Waiting for deployments..."
kubectl wait \
    -n "${NAMESPACE}" \
    --for=condition=available deployment \
    --all \
    --timeout=120s

echo "Cluster ready."