"""
NumPy 2.x and PyInstaller compatibility shim.
Ensures openpyxl (and any third-party libraries expecting legacy NumPy type aliases)
can safely load without raising:
    AttributeError: module 'numpy' has no attribute 'short'
"""
import sys

def apply_numpy_compat():
    try:
        import numpy as np
        
        # All 28 numeric / boolean scalar types expected by openpyxl/compat/numbers.py
        legacy_attrs = {
            'short': getattr(np, 'int16', int),
            'ushort': getattr(np, 'uint16', int),
            'intc': getattr(np, 'int32', int),
            'uintc': getattr(np, 'uint32', int),
            'int_': getattr(np, 'int_', getattr(np, 'int64', int)),
            'uint': getattr(np, 'uint', getattr(np, 'uint64', int)),
            'longlong': getattr(np, 'int64', int),
            'ulonglong': getattr(np, 'uint64', int),
            'half': getattr(np, 'float16', float),
            'float16': getattr(np, 'float16', float),
            'single': getattr(np, 'float32', float),
            'double': getattr(np, 'float64', float),
            'longdouble': getattr(np, 'longdouble', float),
            'int8': getattr(np, 'int8', int),
            'int16': getattr(np, 'int16', int),
            'int32': getattr(np, 'int32', int),
            'int64': getattr(np, 'int64', int),
            'uint8': getattr(np, 'uint8', int),
            'uint16': getattr(np, 'uint16', int),
            'uint32': getattr(np, 'uint32', int),
            'uint64': getattr(np, 'uint64', int),
            'intp': getattr(np, 'intp', int),
            'uintp': getattr(np, 'uintp', int),
            'float32': getattr(np, 'float32', float),
            'float64': getattr(np, 'float64', float),
            'bool_': getattr(np, 'bool_', bool),
            'floating': getattr(np, 'floating', float),
            'integer': getattr(np, 'integer', int),
        }
        
        for attr, target in legacy_attrs.items():
            if not hasattr(np, attr):
                try:
                    setattr(np, attr, target)
                except Exception:
                    pass
    except Exception:
        pass

# Automatically execute on import
apply_numpy_compat()
