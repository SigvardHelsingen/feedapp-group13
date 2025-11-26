output "broker_ips" {
  description = "Broker VM IP addresses"
  value = {
    broker1 = {
      public  = azurerm_public_ip.broker[0].ip_address
      private = azurerm_network_interface.broker[0].private_ip_address
    }
    broker2 = {
      public  = azurerm_public_ip.broker[1].ip_address
      private = azurerm_network_interface.broker[1].private_ip_address
    }
    broker3 = {
      public  = azurerm_public_ip.broker[2].ip_address
      private = azurerm_network_interface.broker[2].private_ip_address
    }
  }
}

output "coordinator_ip" {
  description = "Coordinator VM IP addresses"
  value = {
    public  = azurerm_public_ip.coordinator.ip_address
    private = azurerm_network_interface.coordinator.private_ip_address
  }
}

output "ssh_config" {
  description = "Addendum to SSH config"
  value = <<-EOT
    Host broker-1
        HostName ${azurerm_public_ip.broker[0].ip_address}
        User ${var.admin_username}
        IdentityFile ${substr(var.ssh_public_key_path, 0, length(var.ssh_public_key_path) - 4)}
    
    Host broker-2
        HostName ${azurerm_public_ip.broker[1].ip_address}
        User ${var.admin_username}
        IdentityFile ${substr(var.ssh_public_key_path, 0, length(var.ssh_public_key_path) - 4)}
    
    Host broker-3
        HostName ${azurerm_public_ip.broker[2].ip_address}
        User ${var.admin_username}
        IdentityFile ${substr(var.ssh_public_key_path, 0, length(var.ssh_public_key_path) - 4)}
    
    Host coordinator
        HostName ${azurerm_public_ip.coordinator.ip_address}
        User ${var.admin_username}
        IdentityFile ${substr(var.ssh_public_key_path, 0, length(var.ssh_public_key_path) - 4)}
  EOT
}

output "remote_hosts_file" {
  description = "Put this in ../scripts/for-remote/hosts"
  value = <<-EOT
    ${azurerm_network_interface.broker[0].private_ip_address} broker1
    ${azurerm_network_interface.broker[1].private_ip_address} broker2
    ${azurerm_network_interface.broker[2].private_ip_address} broker3
    ${azurerm_network_interface.coordinator.private_ip_address} coordinator
  EOT
}