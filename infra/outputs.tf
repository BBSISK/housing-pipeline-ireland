output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "storage_account" {
  value = azurerm_storage_account.lake.name
}

output "blob_endpoint" {
  value = azurerm_storage_account.lake.primary_blob_endpoint
}

output "containers" {
  value = sort([for c in azurerm_storage_container.layer : c.name])
}
