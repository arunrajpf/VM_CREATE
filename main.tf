provider "vra" {
  url           = var.url
  access_token  = var.access_token
  insecure      = var.insecure
}

data "vra_project" "this" {
  name = var.project
}

data "vra_catalog_item" "this" {
 name = var.catalog_item_name
 expand_versions = true
}

resource "random_string" "random_id" {
  length  = 4
  upper   = false
  number  = false
  lower   = true
  special = false
}

resource "vra_deployment" "this" {
  count           = var.deployment_count
  project_id      = data.vra_project.this.id
  name            = "${var.deployment_name}-${random_string.random_id.result}-${count.index}"
  description     = var.description
  catalog_item_id = data.vra_catalog_item.this.id
  inputs = {
    inCount         = var.instance_count
    vmName          = var.vmname
    inFlavor        = var.flavor
    inTenant        = var.tenant
    inRail          = var.rail
    inTags          = var.tags
    inCMI           = var.cmi
    inIpv           = var.ipv
    inBootCapacity  = var.bootcapacity
    inSize          = var.extracapacity
    inConfig        = var.cloud_init
  }

  timeouts {
    create = var.tocreate
    delete = var.todelete
  }
}

locals {
  all_deployments = flatten(vra_deployment.this)
  all_resources   = flatten(local.all_deployments.*.resources)
  all_properties  = vra_deployment.this[*].resources.*.properties_json
  vm_name_with_ip = {
    for resource in flatten(vra_deployment.this[*].resources) :
    jsondecode(resource.properties_json).resourceName => jsondecode(resource.properties_json).address
    if resource.type == "Cloud.vSphere.Machine"
  }
}

output "resources" {
  description = "All the resources from a vRA deployment"
  value       = local.all_resources
}

output "resources_properties" {
  description = "Properties of all resources from a vRA deployment"
  value       = local.all_properties
}

output "vm_name_with_ip" {
  value = local.vm_name_with_ip
}
