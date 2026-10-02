package ingest

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"unicode"
)

type Alert struct {
	Status       string            `json:"status"`
	Labels       map[string]string `json:"labels"`
	Annotations  map[string]string `json:"annotations"`
	Fingerprint  string            `json:"fingerprint"`
	GeneratorURL string            `json:"generatorURL"`
}

type Handler struct {
	Secret          []byte
	SignatureHeader string
	Dispatch        func(Alert, string) error
}

var labelValue = regexp.MustCompile(`^[A-Za-z0-9._:-]{1,128}$`)

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(io.LimitReader(r.Body, 256<<10+1))
	if err != nil || len(body) > 256<<10 {
		http.Error(w, "body too large", http.StatusRequestEntityTooLarge)
		return
	}
	if sig := r.Header.Get(h.SignatureHeader); sig != "" {
		mac := hmac.New(sha256.New, h.Secret)
		mac.Write(body)
		got, _ := hex.DecodeString(strings.TrimPrefix(sig, "sha256="))
		if !hmac.Equal(mac.Sum(nil), got) {
			http.Error(w, "bad signature", http.StatusUnauthorized)
			return
		}
	}
	var p struct {
		Version  string  `json:"version"`
		Receiver string  `json:"receiver"`
		Status   string  `json:"status"`
		Alerts   []Alert `json:"alerts"`
	}
	dec := json.NewDecoder(bytes.NewReader(body))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&p); err != nil || len(p.Alerts) == 0 || len(p.Alerts) > 20 {
		http.Error(w, "malformed payload", http.StatusBadRequest)
		return
	}
	for _, a := range p.Alerts {
		if err := validate(a); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
	}
	for _, a := range p.Alerts {
		if a.Status == "firing" {
			if err := h.Dispatch(a, p.Receiver); err != nil {
				http.Error(w, "dispatch refused", http.StatusServiceUnavailable)
				return
			}
		}
	}
	w.WriteHeader(http.StatusAccepted)
}

func validate(a Alert) error {
	for _, k := range []string{"alertname", "team", "cluster", "namespace"} {
		if !labelValue.MatchString(a.Labels[k]) {
			return fmt.Errorf("label %s is missing or invalid", k)
		}
	}
	for k, v := range a.Annotations {
		bad := strings.IndexFunc(v, func(r rune) bool {
			return unicode.Is(unicode.Cf, r) || (unicode.IsControl(r) && r != '\n' && r != '\t')
		})
		if len(v) > 4000 || bad >= 0 {
			return fmt.Errorf("annotation %s is too long or has control characters", k)
		}
	}
	return nil
}
