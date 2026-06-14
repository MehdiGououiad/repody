{{- define "audit-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "audit-platform.fullname" -}}
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

{{- define "audit-platform.labels" -}}
helm.sh/chart: {{ include "audit-platform.name" . }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: audit-platform
{{- end }}

{{- define "audit-platform.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "audit-platform.secretName" -}}
{{ include "audit-platform.fullname" . }}-secrets
{{- end }}

{{- define "audit-platform.minioEndpoint" -}}
{{- if .Values.externalObjectStorage.enabled -}}
{{- .Values.externalObjectStorage.endpoint -}}
{{- else -}}
{{ .Release.Name }}-minio:9000
{{- end -}}
{{- end }}

{{- define "audit-platform.dataPlaneEnv" -}}
{{- if .Values.externalDatabase.enabled }}
- name: AUDIT_DATABASE_URL
  value: {{ .Values.externalDatabase.url | quote }}
{{- else if .Values.postgresql.enabled }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Release.Name }}-postgresql
      key: password
- name: AUDIT_DATABASE_URL
  value: postgresql+asyncpg://{{ .Values.postgresql.auth.username }}:$(POSTGRES_PASSWORD)@{{ .Release.Name }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- end }}
{{- if .Values.externalRedis.enabled }}
- name: AUDIT_REDIS_URL
  value: {{ .Values.externalRedis.url | quote }}
{{- else if .Values.redis.enabled }}
- name: AUDIT_REDIS_URL
  value: redis://{{ .Release.Name }}-redis-master:6379/0
{{- end }}
- name: AUDIT_MINIO_ENDPOINT
  value: {{ include "audit-platform.minioEndpoint" . | quote }}
- name: AUDIT_MINIO_BUCKET
  value: {{ .Values.externalObjectStorage.bucket | default "audit-documents" | quote }}
{{- if .Values.externalObjectStorage.enabled }}
- name: AUDIT_MINIO_ACCESS_KEY
  value: {{ .Values.externalObjectStorage.accessKey | quote }}
- name: AUDIT_MINIO_SECRET_KEY
  value: {{ .Values.externalObjectStorage.secretKey | quote }}
{{- else if .Values.minio.enabled }}
- name: AUDIT_MINIO_ACCESS_KEY
  value: {{ .Values.minio.auth.rootUser | quote }}
- name: AUDIT_MINIO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Release.Name }}-minio
      key: root-password
{{- end }}
{{- if .Values.hatchet.enabled }}
- name: HATCHET_CLIENT_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ include "audit-platform.fullname" . }}-hatchet-token
      key: token
      optional: true
{{- end }}
{{- end }}

{{- define "audit-platform.waitHatchetTokenInit" -}}
{{- if and .Values.hatchet.enabled (not .Values.hatchet.clientToken) .Values.hatchet.bootstrapToken }}
- name: wait-hatchet-token
  image: busybox:1.36
  command:
    - sh
    - -c
    - |
      echo "Waiting for Hatchet client token secret..."
      for i in $(seq 1 120); do
        if [ -s /hatchet/token ]; then
          echo "Hatchet token ready"
          exit 0
        fi
        sleep 3
      done
      echo "Timed out waiting for Hatchet token — set hatchet.clientToken or check hatchet-token-bootstrap job"
      exit 1
  volumeMounts:
    - name: hatchet-client-token
      mountPath: /hatchet
      readOnly: true
{{- end }}
{{- end }}
