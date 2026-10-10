class ProviderConfigurationError(Exception):
    def __init__(self, provider: str, detail: str, error_code: str = "provider_configuration_missing", status_code: int = 400):
        self.provider = provider
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
