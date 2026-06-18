{{- define "inference-llamacpp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "inference-llamacpp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "inference-llamacpp.labels" -}}
helm.sh/chart: {{ include "inference-llamacpp.name" . }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "inference-llamacpp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: repody
app.kubernetes.io/component: inference
{{- end }}

{{- define "inference-llamacpp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "inference-llamacpp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "inference-llamacpp.openaiBaseUrl" -}}
http://{{ include "inference-llamacpp.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.port }}/v1
{{- end }}
