from decimal import Decimal, DefaultContext


# Establish a default decimal context to ensure that we never attempt to save a value with
# too much precision to the database.
DEFAULT_DECIMAL_PRECISION = 10
DEFAULT_DECIMAL_CONTEXT = DefaultContext.copy()
DEFAULT_DECIMAL_CONTEXT.prec = DEFAULT_DECIMAL_PRECISION

TEN_PLACES = Decimal(10) ** -10
TWO_PLACES = Decimal(10) ** -2
