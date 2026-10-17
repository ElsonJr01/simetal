"""Exceções do núcleo de cálculo."""


class CoreError(Exception):
    """Base de todos os erros do núcleo."""


class InvalidInputError(CoreError):
    """Dado de entrada inválido (desvio-padrão zero, dimensões incompatíveis...)."""


class SingularSystemError(CoreError):
    """Sistema indeterminado ou inconsistente (matriz sem posto completo)."""


class FlowsheetError(CoreError):
    """Fluxograma mal definido (fluxo sem ligação, operação isolada...)."""
