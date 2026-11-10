{{- define "repody.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{- define "repody.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: repody
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/* Selector labels for one component: (dict "root" $ "component" "api") */}}
{{- define "repody.selectorLabels" -}}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/* image reference: (dict "image" .Values.images.backend "root" $) — digest wins over tag */}}
{{- define "repody.image" -}}
{{- if .image.digest -}}
{{- printf "%s@%s" .image.repository .image.digest -}}
{{- else -}}
{{- printf "%s:%s" .image.repository (.image.tag | default .root.Chart.AppVersion | toString) -}}
{{- end -}}
{{- end }}

{{/* Pod spec fields shared by every workload (restricted PSA + OpenShift restricted-v2). */}}
{{- define "repody.podDefaults" -}}
automountServiceAccountToken: false
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
{{- with .root.Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .root.Values.topologySpreadConstraints }}
topologySpreadConstraints:
  - maxSkew: {{ .maxSkew }}
    topologyKey: {{ .topologyKey }}
    whenUnsatisfiable: {{ .whenUnsatisfiable }}
    labelSelector:
      matchLabels:
        {{- include "repody.selectorLabels" $ | nindent 8 }}
{{- end }}
{{- end }}

{{/* Every container: no privileges, and a read-only root filesystem (writable paths are
emptyDir volumes: /tmp everywhere, the Next.js cache on the web pods). */}}
{{- define "repody.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop: [ALL]
readOnlyRootFilesystem: true
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/* Backend containers: settings from the ConfigMap. */}}
{{- define "repody.backendEnvFrom" -}}
envFrom:
  - configMapRef:
      name: {{ include "repody.fullname" . }}-config
{{- end }}

{{/* Only the Secret keys the API and workers read (not the web's Better Auth secrets). */}}
{{- define "repody.backendSecretEnv" -}}
{{- $secret := required "existingSecret is required" .Values.existingSecret -}}
{{- range $key := list "AUDIT_DATABASE_URL" "AUDIT_REDIS_URL" "AUDIT_S3_ACCESS_KEY" "AUDIT_S3_SECRET_KEY" }}
- name: {{ $key }}
  valueFrom:
    secretKeyRef: { name: {{ $secret }}, key: {{ $key }} }
{{- end }}
- name: AUDIT_LLAMACPP_API_KEY
  valueFrom:
    secretKeyRef: { name: {{ $secret }}, key: AUDIT_LLAMACPP_API_KEY, optional: true }
# Errors go to Bugsink through the Sentry SDK.
- name: SENTRY_DSN
  valueFrom:
    secretKeyRef: { name: {{ $secret }}, key: BUGSINK_DSN, optional: true }
{{- end }}
