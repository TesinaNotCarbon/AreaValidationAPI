class ValidationInfraError(Exception):
    """Base exception for infrastructure-related validation failures."""


class BlockchainReadError(ValidationInfraError):
    """Raised when on-chain approved IDs cannot be read safely."""


class IPFSDownloadError(ValidationInfraError):
    """Raised when one or more IPFS resources cannot be downloaded."""


class GeometryValidationError(Exception):
    """Raised when the input geometry is malformed or invalid."""
