variable "subscription_id" {
  description = "Azure subscription ID (an identifier, not a secret)."
  type        = string
}

variable "location" {
  description = "Azure region. North Europe is Dublin, so the data stays in Ireland."
  type        = string
  default     = "northeurope"
}

variable "enable_budget" {
  description = "Create the monthly budget alert. Set false if the subscription offer doesn't support budgets."
  type        = bool
  default     = true
}

variable "monthly_budget" {
  description = "Monthly budget for the resource group, in the subscription's billing currency."
  type        = number
  default     = 10
}

variable "budget_start_date" {
  description = "First day of the first budget month, RFC 3339 (must be the first of a month)."
  type        = string
  default     = "2026-10-01T00:00:00Z"
}

variable "budget_emails" {
  description = "Who gets budget alerts."
  type        = list(string)
  default     = []
}
