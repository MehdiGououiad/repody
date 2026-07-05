{{- define "repody-data.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: repody
app.kubernetes.io/component: data
{{- end }}

{{- define "repody-data.postgresql.fullname" -}}
{{ .Release.Name }}-postgresql
{{- end }}

{{- define "repody-data.redis.fullname" -}}
{{ .Release.Name }}-redis-master
{{- end }}

{{- define "repody-data.minio.fullname" -}}
{{ .Release.Name }}-minio
{{- end }}

{{- define "repody-data.image" -}}
{{- $registry := .registry | default "docker.io" -}}
{{- $repository := required "image repository is required" .repository -}}
{{- $tag := required "image tag is required" .tag -}}
{{- if $registry -}}
{{ printf "%s/%s:%s" $registry $repository $tag }}
{{- else -}}
{{ printf "%s:%s" $repository $tag }}
{{- end -}}
{{- end }}

{{- define "repody-data.imagePullSecrets" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}
