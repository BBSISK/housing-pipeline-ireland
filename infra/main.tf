# Housing Pipeline Ireland — Azure foundations (HOUSE-13)
#
# Keyless from the first resource:
#   - storage account keys are switched off (shared_access_key_enabled = false)
#   - Terraform and the pipeline sign in with Entra ID (az login locally, managed identity in Azure)
#   - access is granted by data-plane roles, scoped to this storage account only
# Data stays in Ireland: North Europe is the Dublin region.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.9, < 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6, < 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id

  # Keys are off on the storage account, so the provider must use Entra ID
  # for container operations too.
  storage_use_azuread = true
}

data "azurerm_client_config" "current" {}

locals {
  tags = {
    project = "housing-pipeline-ireland"
    managed = "terraform"
    jira    = "HOUSE"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-housing-pipeline"
  location = var.location
  tags     = local.tags
}

# Storage account names are global, lowercase and at most 24 characters.
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "azurerm_storage_account" "lake" {
  name                     = "sthousing${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  shared_access_key_enabled       = false # keyless: Entra ID only
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"

  blob_properties {
    # Bronze is append-only by design; versioning and soft delete are the safety net.
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = local.tags

  lifecycle {
    prevent_destroy = true # holds data
  }
}

# Medallion layers: raw as landed, cleaned, modelled.
resource "azurerm_storage_container" "layer" {
  for_each              = toset(["bronze", "silver", "gold"])
  name                  = each.key
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"
}

# The person running Terraform can read and write blobs (for uploads from the laptop).
# Data-plane role, scoped to this one storage account. No Owner or Contributor anywhere.
resource "azurerm_role_assignment" "me_blob_contributor" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Spend guard. Some sponsored offers (e.g. Azure for Students) don't support budgets:
# set enable_budget = false in terraform.tfvars if this fails to create.
resource "azurerm_consumption_budget_resource_group" "monthly" {
  count             = var.enable_budget ? 1 : 0
  name              = "budget-housing-pipeline"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.monthly_budget
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    enabled        = true
    threshold      = 50
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.budget_emails
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Forecasted"
    contact_emails = var.budget_emails
  }
}
