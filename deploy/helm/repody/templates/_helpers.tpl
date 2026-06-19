{{- define "repody.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "repody.fullname" -}}
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

{{- define "repody.labels" -}}
helm.sh/chart: {{ include "repody.name" . }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: repody
{{- end }}

{{- define "repody.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "repody.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{ include "repody.fullname" . }}-secrets
{{- end -}}
{{- end }}

{{- define "repody.minioEndpoint" -}}
{{- if .Values.externalObjectStorage.enabled -}}
{{- .Values.externalObjectStorage.endpoint -}}
{{- else -}}
{{ .Release.Name }}-minio:9000
{{- end -}}
{{- end }}

{{- define "repody.dataPlaneEnv" -}}
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
  value: {{ include "repody.minioEndpoint" . | quote }}
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
      name: {{ include "repody.fullname" . }}-hatchet-token
      key: token
      optional: true
{{- end }}
{{- end }}

{{- define "repody.vllmSecretEnv" -}}
- name: AUDIT_VLLM_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "repody.secretName" . }}
      key: AUDIT_VLLM_API_KEY
      optional: true
{{- end }}

{{- define "repody.imagePullSecrets" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{- define "repody.waitHatchetTokenInit" -}}
{{- if and .Values.hatchet.enabled (not .Values.hatchet.clientToken) .Values.hatchet.bootstrapToken }}
- name: wait-hatchet-token
  image: {{ .Values.hatchet.waitInitImage | quote }}
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

{{- define "repody.keycloakJwksUrl" -}}
http://keycloak.{{ .Release.Namespace }}.svc.cluster.local:8080/realms/{{ .Values.keycloak.realm }}/protocol/openid-connect/certs
{{- end }}

{{- define "repody.keycloakAdminUrl" -}}
http://keycloak.{{ .Release.Namespace }}.svc.cluster.local:8080
{{- end }}
