package killswitch

import (
	"context"
	"log/slog"
	"sync/atomic"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/client-go/kubernetes"
)

// Switch watches the control ConfigMap. When halt is "true" it cancels the root context
// that every run, investigator and in-flight tool call derives from, and refuses new runs.
type Switch struct {
	Client          kubernetes.Interface
	Namespace, Name string
	halted          atomic.Bool
}

func (s *Switch) Halted() bool { return s.halted.Load() }

func (s *Switch) Run(ctx context.Context, cancelRoot context.CancelFunc) {
	sel := fields.OneTermEqualSelector("metadata.name", s.Name).String()
	for ctx.Err() == nil {
		w, err := s.Client.CoreV1().ConfigMaps(s.Namespace).Watch(ctx, metav1.ListOptions{FieldSelector: sel})
		if err != nil {
			slog.Error("control watch failed", "err", err)
			time.Sleep(2 * time.Second)
			continue
		}
		for ev := range w.ResultChan() {
			if cm, ok := ev.Object.(*corev1.ConfigMap); ok && cm.Data["halt"] == "true" && !s.halted.Swap(true) {
				slog.Warn("halt flag set; cancelling all runs")
				cancelRoot()
			}
		}
	}
}
