package tools

import (
	"context"
	"encoding/json"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"

	"github.com/northwind-platform/cloudops-agent/internal/config"
)

const maxReplicas = 50

type Kube struct {
	Clusters map[string]kubernetes.Interface
	Dynamic  map[string]dynamic.Interface
	Teams    config.Teams
}

func (k *Kube) namespaceFor(call Call) (string, error) {
	ns, _ := call.Args["namespace"].(string)
	if ns == "" || !k.Teams.OwnsNamespace(call.Tenant, ns) {
		return "", fmt.Errorf("namespace %q is not owned by team %s", ns, call.Tenant)
	}
	if _, ok := k.Clusters[call.Cluster]; !ok {
		return "", fmt.Errorf("unknown cluster %q", call.Cluster)
	}
	return ns, nil
}

func (k *Kube) ScaleDeployment(ctx context.Context, call Call) (Result, error) {
	ns, err := k.namespaceFor(call)
	if err != nil {
		return Result{}, err
	}
	name, _ := call.Args["deployment"].(string)
	want, _ := call.Args["replicas"].(float64)
	deps := k.Clusters[call.Cluster].AppsV1().Deployments(ns)
	cur, err := deps.GetScale(ctx, name, metav1.GetOptions{})
	if err != nil {
		return Result{}, err
	}
	replicas := int32(want)
	switch {
	case replicas < 1:
		return Result{}, fmt.Errorf("refusing to scale %s/%s below 1 replica", ns, name)
	case replicas > maxReplicas:
		return Result{}, fmt.Errorf("refusing to scale %s/%s above %d replicas", ns, name, maxReplicas)
	case cur.Spec.Replicas > 0 && replicas > cur.Spec.Replicas*3:
		return Result{}, fmt.Errorf("refusing to more than triple %s/%s in one step", ns, name)
	}
	cur.Spec.Replicas = replicas
	if _, err := deps.UpdateScale(ctx, name, cur, metav1.UpdateOptions{}); err != nil {
		return Result{}, err
	}
	return Result{Content: fmt.Sprintf("scaled %s/%s to %d", ns, name, replicas)}, nil
}

var helmReleases = schema.GroupVersionResource{Group: "helm.toolkit.fluxcd.io", Version: "v2", Resource: "helmreleases"}

// RollbackRelease pins a Flux HelmRelease to an earlier chart version from its history,
// by default the one it ran before the last upgrade.
func (k *Kube) RollbackRelease(ctx context.Context, call Call) (Result, error) {
	ns, err := k.namespaceFor(call)
	if err != nil {
		return Result{}, err
	}
	name, _ := call.Args["release"].(string)
	res := k.Dynamic[call.Cluster].Resource(helmReleases).Namespace(ns)
	hr, err := res.Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return Result{}, err
	}
	history, _, _ := unstructured.NestedSlice(hr.Object, "status", "history")
	if len(history) < 2 {
		return Result{}, fmt.Errorf("release %s/%s has no previous revision", ns, name)
	}
	version, _ := call.Args["to_version"].(string)
	if version == "" {
		version, _ = history[1].(map[string]any)["chartVersion"].(string)
	}
	found := false
	for _, h := range history {
		found = found || h.(map[string]any)["chartVersion"] == version
	}
	if !found {
		return Result{}, fmt.Errorf("chart version %q was never deployed for %s/%s", version, ns, name)
	}
	patch, _ := json.Marshal(map[string]any{"spec": map[string]any{"chart": map[string]any{"spec": map[string]any{"version": version}}}})
	if _, err := res.Patch(ctx, name, types.MergePatchType, patch, metav1.PatchOptions{}); err != nil {
		return Result{}, err
	}
	return Result{Content: fmt.Sprintf("release %s/%s pinned to chart %s", ns, name, version)}, nil
}
