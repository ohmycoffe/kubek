#!/usr/bin/env bash

set -eEuo pipefail

CLUSTER_NAME="kubek-test"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    echo "Usage: $0 TARGET [TARGET...]"
    echo ""
    echo "Sets up a local Kind cluster with test manifests."
    echo ""
    echo "Examples:"
    echo "  $0 kubectl-portfwd              # only portfwd"
    echo "  $0 kubectl-portfwd kubectl-envx  # both"
    exit 0
}

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
fi

TARGETS=("$@")

require() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Error: $1 is required but not found in PATH"
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

echo "Installing Argo Workflows CRDs..."
kubectl apply -k "github.com/argoproj/argo-workflows//manifests/base/crds/minimal?ref=stable"
kubectl wait --for=condition=Established crd/workflowtemplates.argoproj.io --timeout=60s

for target in "${TARGETS[@]}"; do
    manifest="${REPO_ROOT}/${target}/tests/resources/k8s/local-cluster.yaml"

    if [[ ! -f "${manifest}" ]]; then
        echo "Skipping ${target}: no manifest found at ${manifest}"
        continue
    fi
    namespace_name="ns-${target}"
    echo "Setting up namespace ${namespace_name}..."
    kubectl create namespace "${namespace_name}" --dry-run=client -o yaml | kubectl apply -f -

    echo "Applying ${target} manifests..."
    kubectl apply -n "${namespace_name}" -f "${manifest}"
done

echo "Waiting for all deployments..."
for target in "${TARGETS[@]}"; do
    namespace_name="ns-${target}"
    kubectl wait \
        -n "${namespace_name}" \
        --for=condition=available deployment \
        --all \
        --timeout=120s 2>/dev/null || true
done

echo "Cluster ready."
