"""
Utility Functions
Made by Tpmonkey
"""
from typing import Union

int_or_float = Union[int, float] 

def limit(
    number: int_or_float, minimum: int_or_float = None, maximum: int_or_float = None
    ) -> int_or_float:
    """A function to limit int/float value for exceeding intentional limit."""
    if minimum is None and maximum is None:
        # Both is none define. Why would you even do this.
        return number 
    elif minimum is None and maximum is not None:
        # Maximum limit defined, return value must be less than or equal to maximum.
        return min(maximum, number)
    elif minimum is not None and maximum is None: 
        # Minimum limit defined, return value must be more than or equal to minimum
        return max(minimum, number)
    # Both defined, value must be in range.
    return max(min(maximum, number), minimum)