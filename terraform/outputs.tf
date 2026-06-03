# Outputs will be defined as resources are added.
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_region" {
  description = "GKE cluster region"
  value       = var.region
}

output "artifact_registry_url" {
  description = "Docker image base URL for pushing images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/k8s-exercise"
}

output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
}
