{{/*
Expand the name of the chart.
*/}}
{{- define "ebook-tools.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ebook-tools.fullname" -}}
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

{{/*
Common labels
*/}}
{{- define "ebook-tools.labels" -}}
helm.sh/chart: {{ include "ebook-tools.name" . }}-{{ .Chart.Version }}
{{ include "ebook-tools.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ebook-tools.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ebook-tools.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Component-specific labels (pass dict with .root and .component)
*/}}
{{- define "ebook-tools.componentLabels" -}}
{{ include "ebook-tools.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Component-specific selector labels
*/}}
{{- define "ebook-tools.componentSelectorLabels" -}}
{{ include "ebook-tools.selectorLabels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
