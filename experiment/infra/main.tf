terraform {
  required_version = ">= 1.14"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "resource_group_name" {
  default = "rg-messaging-bench"
}

variable "location" {
  default = "norwayeast"
}

variable "admin_username" {
  default = "azureuser"
}

variable "ssh_public_key_path" {
  default = "~/.ssh/azure_rsa.pub"
}

variable "vm_size" {
  default = "Standard_L8as_v3"  # 8 vCPU (EPYC 7763 (Zen 3 7nm 2021)), 64GB RAM, 1.8 TiB local NVMe
}

resource "azurerm_resource_group" "benchmark" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_virtual_network" "benchmark" {
  name                = "vnet-benchmark"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name
}

resource "azurerm_subnet" "benchmark" {
  name                 = "subnet-benchmark"
  resource_group_name  = azurerm_resource_group.benchmark.name
  virtual_network_name = azurerm_virtual_network.benchmark.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "benchmark" {
  name                = "nsg-benchmark"
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "benchmark" {
  subnet_id                 = azurerm_subnet.benchmark.id
  network_security_group_id = azurerm_network_security_group.benchmark.id
}

resource "azurerm_public_ip" "broker" {
  count               = 3
  name                = "pip-broker${count.index + 1}"
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_public_ip" "coordinator" {
  name                = "pip-coordinator"
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "broker" {
  count               = 3
  name                = "nic-broker${count.index + 1}"
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.benchmark.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.broker[count.index].id
  }
}

resource "azurerm_network_interface" "coordinator" {
  name                = "nic-coordinator"
  location            = azurerm_resource_group.benchmark.location
  resource_group_name = azurerm_resource_group.benchmark.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.benchmark.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.coordinator.id
  }
}

resource "azurerm_linux_virtual_machine" "broker" {
  count               = 3
  name                = "vm-broker${count.index + 1}"
  resource_group_name = azurerm_resource_group.benchmark.name
  location            = azurerm_resource_group.benchmark.location
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids = [
    azurerm_network_interface.broker[count.index].id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data = base64encode(file("${path.module}/cloud-init-broker.yaml"))

  tags = {
    role = "broker"
  }
}

resource "azurerm_linux_virtual_machine" "coordinator" {
  name                = "vm-coordinator"
  resource_group_name = azurerm_resource_group.benchmark.name
  location            = azurerm_resource_group.benchmark.location
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids = [
    azurerm_network_interface.coordinator.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data = base64encode(file("${path.module}/cloud-init-coordinator.yaml"))

  tags = {
    role = "coordinator"
  }
}
