variable "access_token" {
    type = string
    description = "An Azure AD access_token"
}

variable "url" {
    type = string
    description = "Base URL to the xCloud AZ"
}

variable "insecure" {
    type = string
    description = "Do not try to validate the vRA Certficate"
}

variable "project" {
    type = string
    description = "The xCloud Project to use in the form of [xCloud Account Name]-[xCloud Account id]"
}
 
variable "deployment_name" {
    type = string
    description = "The name of this deployment (must be unique in this instance)"
}

variable "catalog_item_name" {
    type = string
    description = "Name of the catalog item to deploy"
}

variable "instance_count" {
    type = number
    description = "Number of machines to build"
}

variable "vmname" {
    type = string
    description = "Enter the vm Hostname prefix (up to 8 characters)" 
}

variable "flavor" {
    type = string
    description = "Select the Flavor (CPU/memory size)"
}

variable "tenant" {
    type = string
    description = "Select Network Tenant" 
}

variable "rail" {
    type = string
    description = "Select Network Rail" 
}

variable "tags" {
    type = string
    description = "Additional VM tags in the format name:value,name2:value2"
}

variable "cmi" {
    type = string
    description = "Select the Comcast Machine Image"
}

variable "ipv" {
    type = string
    description = "Select the IP Address type (IPv6 = Single Stack, IPv4_IPv6 = Dual Stack)" 
}

variable "deployment_count" {
    type = number
    description = "Number of deployments to create"
}

variable "description" {
    type = string
    description = "Description of Deployment - Optional"
}

variable "cloud_init" {
    type = string
    description = "Enter any Cloud-init script (user data). Must begin with #cloud-config. See https://cloudinit.readthedocs.io/en/latest/index.html"
}

variable "tocreate" {
    type = string
    description = "Terraform Deployment Creation Timeout 180m is 3 hours"
}

variable "todelete" {
    type = string
    description = "Terraform Deployment Deletion Timeout 180m is 3 hours"
}

variable "bootcapacity" {
    type = number
    description = "Number of GB for system boot disk Capacity default is 50GB"
}

variable "extracapacity" {
    type = number
    description = "Number of GB for extra disk Capacity default is 10GB"
}
