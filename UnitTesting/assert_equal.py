""" Assert SymPy Expression Equality """
# Author: Ken Sible
# Email:  ksible *at* outlook *dot* com

from standard_constants import precision
from mpmath import mp, mpf, mpc, fabs, log10
import sympy as sp, sys, random

def expand_vardict(vardict):
    """ Expand Variable Dictionary

        >>> expand_vardict({ \
                'v': ['0', '1', '2'], \
                'M': [['00', '01', '02'], ['10', '11', '12'], ['20', '21', '22']] \
            }) # doctest: +ELLIPSIS
        {'v[0]': '0', 'v[1]': '1', ... 'M[2][1]': '21', 'M[2][2]': '22'}
    """
    if all(not isinstance(vardict[var], list) for var in vardict):
        return vardict
    for var in vardict:
        if not isinstance(vardict[var], list):
            vardict[var] = [vardict[var]]
    return expand_vardict({(var + '[' + str(i) + ']') if len(vardict[var]) > 1 else var: vardict[var][i]
            for var in vardict for i in range(len(vardict[var]))})

def compute_value(symdict, replaced, reduced, factor):
    # determine the precision for floating point arithmetic
    mp.dps = factor * precision
    # substitute unique random number for each free symbol in symdict
    # into every common subexpression from CSE and into main expression
    for var, subexpr in replaced:
        for symbol in subexpr.free_symbols:
            subexpr = subexpr.subs(symbol, symdict[symbol])
        symdict[var] = subexpr
    reduced = reduced[0]
    for symbol in reduced.free_symbols:
        reduced = reduced.subs(symbol, symdict[symbol])
    reduced = reduced.subs(sp.Function('NRPyAbs'), sp.Abs)
    value = mpc(sp.N(reduced)) if isinstance(reduced, complex) else mpf(reduced)
    mp.dps = precision
    return value

def update_vardict(vardict):
    # expand vardict into component mapping
    vardict = expand_vardict(vardict)
    # extract every free symbol present in vardict
    symdict = {symbol: None for var in vardict if isinstance(vardict[var], sp.Basic)
                   for symbol in vardict[var].free_symbols}
    for free_symbol in symdict:
        # seed random number generator with free_symbol hash value
        random.seed(hash(free_symbol))
        # update symdict with mapping: free_symbol -> unique random number
        symdict[free_symbol] = mpf(random.random())
    for var in vardict:
        # apply CSE to every expression in vardict
        replaced, reduced = sp.cse(vardict[var], order='none')
        # calculate value after substituting the unique random number
        # from each free symbol in symdict into every expression in vardict
        value = compute_value(symdict, replaced, reduced, factor=1)
        # double the precision (factor = 2) whenever value within range of zero
        if fabs(value) != mpf('0.0') and fabs(value) < 10 ** ((-2.0/3) * precision):
            _value = compute_value(symdict, replaced, reduced, factor=2)
            if fabs(_value) < 10 ** (-(4.0/3) * precision):
                value = mpf('0.0')
        # update vardict with mapping: variable -> (pseudo) unique number
        vardict[var] = value
    return vardict

def assert_equal(vardict_1, vardict_2):
    """ Assert SymPy Expression Equality

        >>> from sympy import sin, cos
        >>> from sympy.abc import x

        >>> assert_equal(sin(2*x), 2*sin(x)*cos(x))
        >>> assert_equal(cos(2*x), cos(x)**2 - sin(x)**2)

        >>> assert_equal(cos(2*x), 1 - 2*sin(x)**2)
        >>> assert_equal(cos(2*x), 1 + 2*sin(x)**2)
        Traceback (most recent call last):
        ...
        AssertionError

        >>> vardict_1 = {'A': sin(2*x), 'B': cos(2*x)}
        >>> vardict_2 = {'A': 2*sin(x)*cos(x), 'B': cos(x)**2 - sin(x)**2}
        >>> assert_equal(vardict_1, vardict_2)
    """
    if isinstance(vardict_1, sp.Basic):
        vardict_1 = {'': vardict_1}
    if isinstance(vardict_2, sp.Basic):
        vardict_2 = {'': vardict_2}
    # update each vardict with mapping: variable -> (pseudo) unique number
    vardict_1, vardict_2 = update_vardict(vardict_1), update_vardict(vardict_2)
    # assert whether SDA >= (2/3) * precision, implying expression equality
    for var_1, var_2 in zip(vardict_1, vardict_2):
        n_1, n_2 = vardict_1[var_1], vardict_2[var_2]
        E_rel = 2 * fabs(n_1 - n_2)/(fabs(n_1) + fabs(n_2))
        assert -log10(E_rel) + 1 >= (2.0/3) * precision

if __name__ == "__main__":
    import doctest
    sys.exit(doctest.testmod()[0])
