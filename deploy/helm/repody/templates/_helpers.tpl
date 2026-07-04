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

{{- define "repody.restrictedCompatibility" -}}
{{- $restricted := true -}}
{{- with .Values.platform -}}
{{- with .compatibility -}}
{{- if hasKey . "restricted" -}}
{{- $restricted = .restricted -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- $restricted -}}
{{- end }}

{{- define "repody.podSecurityContext" -}}
{{- if eq (include "repody.restrictedCompatibility" . | trim) "true" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- else -}}
{}
{{- end -}}
{{- end }}

{{- define "repody.containerSecurityContext" -}}
{{- if eq (include "repody.restrictedCompatibility" . | trim) "true" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- else -}}
{}
{{- end -}}
{{- end }}

{{- define "repody.initContainerSecurityContext" -}}
{{- if eq (include "repody.restrictedCompatibility" . | trim) "true" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- else -}}
{}
{{- end -}}
{{- end }}

{{- define "repody.imageRepository" -}}
{{- $repo := .repo -}}
{{- $registry := .root.Values.global.imageRegistry | default "" -}}
{{- if and $registry (not (contains "/" $repo)) -}}
{{- printf "%s/%s" $registry $repo -}}
{{- else -}}
{{- $repo -}}
{{- end -}}
{{- end }}

{{- define "repody.backendImageRepository" -}}
{{- $repo := coalesce .Values.images.backend.repository .Values.images.api.repository .Values.images.worker.repository "repody-backend" -}}
{{- include "repody.imageRepository" (dict "root" . "repo" $repo) -}}
{{- end }}

{{- define "repody.webImageRepository" -}}
{{- $repo := .Values.images.web.repository | default "repody-web" -}}
{{- include "repody.imageRepository" (dict "root" . "repo" $repo) -}}
{{- end }}

{{- define "repody.backendImageTag" -}}
{{- coalesce .Values.images.backend.tag .Values.images.api.tag .Values.images.worker.tag .Chart.AppVersion -}}
{{- end }}

{{- define "repody.backendImagePullPolicy" -}}
{{- coalesce .Values.images.backend.pullPolicy .Values.images.api.pullPolicy .Values.images.worker.pullPolicy "IfNotPresent" -}}
{{- end }}

{{- define "repody.backendImage" -}}
{{- printf "%s:%s" (include "repody.backendImageRepository" .) (include "repody.backendImageTag" .) -}}
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
  {{- if .Values.externalDatabase.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ .Values.externalDatabase.existingSecret }}
      key: {{ .Values.externalDatabase.urlKey }}
  {{- else }}
  value: {{ .Values.externalDatabase.url | quote }}
  {{- end }}
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
  {{- if .Values.externalRedis.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ .Values.externalRedis.existingSecret }}
      key: {{ .Values.externalRedis.urlKey }}
  {{- else }}
  value: {{ .Values.externalRedis.url | quote }}
  {{- end }}
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
  {{- if .Values.externalObjectStorage.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ .Values.externalObjectStorage.existingSecret }}
      key: {{ .Values.externalObjectStorage.accessKeyKey }}
  {{- else }}
  value: {{ .Values.externalObjectStorage.accessKey | quote }}
  {{- end }}
- name: AUDIT_MINIO_SECRET_KEY
  {{- if .Values.externalObjectStorage.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ .Values.externalObjectStorage.existingSecret }}
      key: {{ .Values.externalObjectStorage.secretKeyKey }}
  {{- else }}
  value: {{ .Values.externalObjectStorage.secretKey | quote }}
  {{- end }}
{{- else if .Values.minio.enabled }}
- name: AUDIT_MINIO_ACCESS_KEY
  value: {{ .Values.minio.auth.rootUser | quote }}
- name: AUDIT_MINIO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Release.Name }}-minio
      key: root-password
{{- end }}
{{- end }}

{{- define "repody.bugsinkEnv" -}}
{{- if .Values.observability.existingSecret }}
- name: BUGSINK_DSN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.observability.existingSecret }}
      key: {{ .Values.observability.bugsinkDsnKey }}
      optional: true
{{- else if .Values.observability.bugsinkDsn }}
- name: BUGSINK_DSN
  value: {{ .Values.observability.bugsinkDsn | quote }}
{{- end }}
{{- end }}

{{- define "repody.webBugsinkEnv" -}}
{{- if .Values.observability.existingSecret }}
- name: BUGSINK_DSN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.observability.existingSecret }}
      key: {{ .Values.observability.bugsinkDsnKey }}
      optional: true
- name: NEXT_PUBLIC_BUGSINK_DSN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.observability.existingSecret }}
      key: {{ .Values.observability.bugsinkDsnKey }}
      optional: true
{{- else if .Values.observability.bugsinkDsn }}
- name: NEXT_PUBLIC_BUGSINK_DSN
  value: {{ .Values.observability.bugsinkDsn | quote }}
- name: BUGSINK_DSN
  value: {{ .Values.observability.bugsinkDsn | quote }}
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

{{- define "repody.waitPostgresInit" -}}
{{- if and .Values.externalDatabase.enabled .Values.externalDatabase.host }}
- name: wait-postgres
  image: {{ .Values.init.waitImage | quote }}
  securityContext:
    {{- include "repody.initContainerSecurityContext" . | nindent 4 }}
  command:
    - sh
    - -c
    - |
      host="{{ .Values.externalDatabase.host }}"
      port="{{ .Values.externalDatabase.port | default 5432 }}"
      echo "Waiting for PostgreSQL at ${host}:${port}..."
      for i in $(seq 1 90); do
        if nc -z "${host}" "${port}" 2>/dev/null; then
          echo "PostgreSQL is accepting connections"
          exit 0
        fi
        sleep 3
      done
      echo "Timed out waiting for PostgreSQL" >&2
      exit 1
{{- else if and .Values.postgresql.enabled (not .Values.externalDatabase.enabled) }}
- name: wait-postgres
  image: {{ .Values.init.waitImage | quote }}
  securityContext:
    {{- include "repody.initContainerSecurityContext" . | nindent 4 }}
  command:
    - sh
    - -c
    - |
      host="{{ .Release.Name }}-postgresql"
      echo "Waiting for PostgreSQL at ${host}:5432..."
      for i in $(seq 1 90); do
        if nc -z "${host}" 5432 2>/dev/null; then
          echo "PostgreSQL is accepting connections"
          exit 0
        fi
        sleep 3
      done
      echo "Timed out waiting for PostgreSQL" >&2
      exit 1
{{- end }}
{{- end }}

{{- define "repody.keycloakJwksUrl" -}}
{{- if .Values.gatewayApi.authServiceNamespace -}}
http://{{ .Values.gatewayApi.authServiceName | default "keycloak" }}.{{ .Values.gatewayApi.authServiceNamespace }}.svc.cluster.local:{{ .Values.gatewayApi.authServicePort | default 8080 }}/realms/{{ .Values.keycloak.realm }}/protocol/openid-connect/certs
{{- else -}}
http://keycloak.{{ .Release.Namespace }}.svc.cluster.local:8080/realms/{{ .Values.keycloak.realm }}/protocol/openid-connect/certs
{{- end -}}
{{- end }}

{{- define "repody.keycloakAdminUrl" -}}
{{- if .Values.config.keycloakAdminUrl -}}
{{- .Values.config.keycloakAdminUrl -}}
{{- else if .Values.gatewayApi.authServiceNamespace -}}
http://{{ .Values.gatewayApi.authServiceName | default "keycloak" }}.{{ .Values.gatewayApi.authServiceNamespace }}.svc.cluster.local:{{ .Values.gatewayApi.authServicePort | default 8080 }}
{{- else -}}
http://keycloak.{{ .Release.Namespace }}.svc.cluster.local:8080
{{- end -}}
{{- end }}
