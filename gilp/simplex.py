import numpy as np
import itertools
from scipy.linalg import solve
from typing import List, Tuple

"""Provides an implementation of the revised simplex method.

Classes:
    UnboundedLinearProgram: Exception indicating the unboundedness of an LP.
    InvalidBasis: Exception indicating a list of indices does not form a basis.
    InfeasibleBasicSolution: Exception indicating infeasible bfs.
    LP: Maintains the coefficents and size of a linear program (LP).

Functions:
    invertible: Return true if the matrix A is invertible.
    equality_form: Return the LP in standard equality form.
    phase_one: Execute Phase 1 of the simplex method.
    simplex_iter: Execute a single iteration of the revised simplex method.
    simplex: Run the revised simplex method.
"""


class UnboundedLinearProgram(Exception):
    """Raised when an LP is found to be unbounded during an execution of the
    revised simplex method"""
    pass


class InvalidBasis(Exception):
    """Raised when a list of indices does not form a valid basis and prevents
    further correct execution of the function."""
    pass


class Infeasible(Exception):
    """Raised when an LP is found to have no feasible solution."""
    pass


class InfeasibleBasicSolution(Exception):
    """Raised when a list of indices forms a valid basis but the corresponding
    basic solution is infeasible."""
    pass


class LP:
    """Maintains the coefficents and size of a linear program (LP).

    The LP class maintains the coefficents of a linear program in either
    standard equality or inequality form. A is an m*n matrix describing the
    linear combination of variables making up the LHS of each constraint. b is
    a vector of length m making up the RHS of each constraint. Lastly, c is a
    vector of length n describing the objective function to be maximized. The
    n decision variables are all nonnegative.

    ::

        inequality        equality
        max c^Tx          max c^Tx
        s.t Ax <= b       s.t Ax == b
             x >= 0            x >= 0

    Attributes:
        n (int): number of decision variables.
        m (int): number of constraints (excluding nonnegativity constraints).
        A (np.ndarray): An m*n matrix of coefficients.
        b (np.ndarray): A vector of coefficients of length m.
        c (np.ndarray): A vector of coefficients of length n.
        equality (bool): True iff the LP is in standard equality form.
    """

    def __init__(self,
                 A: np.ndarray,
                 b: np.ndarray,
                 c: np.ndarray,
                 equality: bool = False):
        """Initializes an LP.

        Creates an instance of LP using the given coefficents interpreted as
        either inequality or equality form.

        ::

            inequality        equality
            max c^Tx          max c^Tx
            s.t Ax <= b       s.t Ax == b
                x >= 0            x >= 0

        Args:
            A (np.ndarray): An m*n matrix of coefficients.
            b (np.ndarray): A vector of coefficients of length m.
            c (np.ndarray): A vector of coefficients of length n.
            equality (bool): True iff the LP is in standard equality form.

        Raises:
            ValueError: b should have shape (m,1) or (m) but was ().
            ValueError: b is not nonnegative. Was [].
            ValueError: c should have shape (n,1) or (n) but was ().
        """
        self.equality = equality
        self.m = len(A)
        self.n = len(A[0])
        self.A = np.copy(A)

        if len(b.shape) == 1 and b.shape[0] == self.m:
            self.b = np.array([b]).transpose()
        elif len(b.shape) == 2 and b.shape == (self.m, 1):
            self.b = np.copy(b)
        else:
            m = str(self.m)
            raise ValueError('b should have shape (' + m + ',1) '
                             + 'or (' + m + ') but was ' + str(b.shape) + '.')

        if len(c.shape) == 1 and c.shape[0] == self.n:
            self.c = np.array([c]).transpose()
        elif len(c.shape) == 2 and c.shape == (self.n, 1):
            self.c = np.copy(c)
        else:
            n = str(self.n)
            raise ValueError('c should have shape (' + n + ',1) '
                             + 'or (' + n + ') but was ' + str(c.shape) + '.')

    def get_coefficients(self):
        """Returns n,m,A,b,c describing this LP."""
        return (self.n, self.m,
                np.copy(self.A), np.copy(self.b), np.copy(self.c))

    def get_basic_feasible_sol(self,
                               B: List[int],
                               feasibility_tol: float = 1e-7) -> np.ndarray:
        """Return the basic feasible solution corresponding to this basis.

        By definition, B is a basis iff A_B is invertible (where A is the
        matrix of coefficents in standard equality form). The corresponding
        basic solution x satisfies A_Bx = b. By definition, x is a basic
        feasible solution iff x satisfies both A_Bx = b and x > 0. These
        constraints must be satisfied to a tolerance of feasibility_tol
        (which is set to 1e-7 by default).

        Args:
            B (List[int]): A list of indices in {0..n+m-1} forming a basis.
            feasibility_tol (float): Primal feasibility tolerance (1e-7 default).

        Returns:
            np.ndarray: Basic feasible solution corresponding to the basis B.

        Raises:
            InvalidBasis: B
            InfeasibleBasicSolution: x_B
        """
        n,m,A,b,c = equality_form(self).get_coefficients()
        B.sort()
        if B[-1] < n and invertible(A[:,B]):
            x_B = np.zeros((n, 1))
            x_B[B,:] = solve(A[:,B], b)
            if all(x_B >= np.zeros((n, 1)) - feasibility_tol):
                return x_B
            else:
                raise InfeasibleBasicSolution(x_B)
        else:
            raise InvalidBasis(B)

    def get_basic_feasible_solns(self) -> Tuple[List[np.ndarray],
                                                List[List[int]],
                                                List[float]]:
        """Return all basic feasible solutions, their basis, and objective value.

        Returns:
            Tuple:

            - List[np.ndarray]: The list of basic feasible solutions for this LP.
            - List[List[int]]: The corresponding list of bases.
            - List[float]: The corresponding list of objective values.
        """
        n,m,A,b,c = equality_form(self).get_coefficients()
        bfs, bases, values = [], [], []
        for B in itertools.combinations(range(n), m):
            try:
                x_B = self.get_basic_feasible_sol(list(B))
                bfs.append(x_B)
                bases.append(list(B))
                values.append(float(np.dot(c.transpose(), x_B)))
            except (InvalidBasis, InfeasibleBasicSolution):
                pass
        return (bfs, bases, values)

    def get_tableau(self, B: List[int]) -> np.ndarray:
        """Return the tableau corresponding to the basis B for this LP.

        The returned tableau has the following form::

            z - (c_N^T - y^TA_N)x_N = y^Tb  where   y^T = c_B^TA_B^(-1)
            x_B + A_B^(-1)A_Nx_N = x_B^*    where   x_B^* = A_B^(-1)b

        Args:
            B (List[int]): A valid basis for this LP

        Returns:
            np.ndarray: A numpy array representing the tableau

        Raises:
            InvalidBasis: Invalid basis. A_B is not invertible.
        """
        n,m,A,b,c = equality_form(self).get_coefficients()
        if not invertible(A[:,B]):
            raise InvalidBasis('Invalid basis. A_B is not invertible.')

        N = list(set(range(n)) - set(B))
        B.sort()
        N.sort()
        A_B_inv = np.linalg.inv(A[:,B])
        yT = np.dot(c[B,:].transpose(), A_B_inv)

        T = np.zeros((m+1, n+2))
        T[0,0] = 1
        T[0,1:n+1][N] = -(c[N,:].transpose() - np.dot(yT, A[:,N]))
        T[0,n+1] = np.dot(yT,b)
        T[1:,1:n+1][:,N] = np.dot(A_B_inv, A[:,N])
        T[1:,1:n+1][:,B] = np.identity(len(B))
        T[1:,n+1] = np.dot(A_B_inv, b)[:,0]
        return T


def invertible(A:np.ndarray) -> bool:
    """Return true if the matrix A is invertible.

    By definition, a matrix A is invertible iff n = m and A has rank n

    Args:
        A (np.ndarray): An m*n matrix

    Returns:
        bool: True if the matrix A is invertible. False otherwise.
    """
    return len(A) == len(A[0]) and np.linalg.matrix_rank(A) == len(A)


def equality_form(lp: LP) -> LP:
    """Return the LP in standard equality form.

    Transform the LP (if needed) into an equivalent LP in standard equality
    form. Furthermore, ensure that every element of b is nonnegative. The
    transformation can be summariazed as follows.

    ::

        inequality        equality
        max c^Tx          max c^Tx
        s.t Ax <= b       s.t Ax + Is == b
             x >= 0                x,s >= 0

    Args:
        lp (LP): An LP in either standard inequality or equality form.

    Returns:
        LP: The corresponding standard equality form LP
    """
    n,m,A,b,c = lp.get_coefficients()
    if not lp.equality:
        # add slack variables
        A = np.hstack((A, np.identity(m)))
        c = np.vstack((c, np.zeros((m, 1))))
    # ensure every element of b is nonnegative
    neg = (b < 0)[:,0]
    b[neg] = -b[neg]
    A[neg,:] = -A[neg,:]
    return LP(A,b,c,equality=True)


def phase_one(lp: LP,
              pivot_rule: str = 'bland',
              feasibility_tol: float = 1e-7) -> Tuple[np.ndarray, List[int]]:
    """Execute Phase 1 of the simplex method.

    Execute Phase 1 of the simplex method (using the given pivot rule) to find
    an inital basic feasible solution to the given LP. Return a basic feasible
    solution if one exists. Otherwise, raise the Infeasible exception.

    Args:
        lp (LP): LP on which phase 1 of the simplex method will be done.
        pivot_rule (str): Pivot rule to be used. 'bland' by default.
        feasibility_tol (float): Primal feasibility tolerance (1e-7 default).

    Returns:
        Tuple:

        - np.ndarray: An initial basic feasible solution.
        - List[int]: Corresponding basis to the initial BFS.

    Raises:
        Infeasible: The LP is found to not have a feasible solution.
    """
    n,m,A,b,c = equality_form(lp).get_coefficients()

    # introduce artificial variables (measure error in constraint)
    A = np.hstack((A,np.identity(m)))
    c = np.zeros((n+m,1))
    c[n:,0] = -1 # minimize sum of artificial variables

    # set B to the list of artificial variables to get initial feasible tableau
    B = list(range(n,n+m))
    x = np.zeros((n+m,1))
    x[B,:] = b

    # solve the auxiliary LP
    aux_lp = LP(A,b,c,equality=True)
    optimal = False
    current_value = float(np.dot(c.transpose(),x))
    while(not optimal):
        x,B,value,opt = simplex_iteration(lp=aux_lp,
                                          x=x,
                                          B=B,
                                          pivot_rule=pivot_rule,
                                          feasibility_tol=feasibility_tol)
        current_value = value
        N = list(set(range(len(x))) - set(B))
        if opt:
            optimal = True

        # get tableau at this iteration
        T = aux_lp.get_tableau(B)
        A = T[1:,1:-1]
        b = np.array([T[1:,-1]]).transpose()

        # delete appearances of nonbasic artificial variables
        subset = list(range(n)) + [x for x in list(range(n,len(x))) if x in B]
        A = A[:,subset]
        c = c[subset,:]
        index_in_basis = np.zeros(len(x))
        index_in_basis[B] = 1
        index_in_basis = index_in_basis[subset]
        B = list(np.nonzero(index_in_basis)[0])
        x = x[subset,:]
        aux_lp = LP(A,b,c,equality=True)

    if current_value < -feasibility_tol:
        # optimal value is strictly positive
        raise Infeasible('The LP has no feasible solutions.')
    else:
        # make changes (if needed) until no basic artificial variable
        while(B[-1] >= n):
            i = B[-1] # artificial variable u_i is still basic
            constr_index = np.nonzero(A[:,i])[0]
            if len(constr_index) != 1:
                raise ValueError('Should only be one non-zero entry because ' +
                                 'this index is basic.')
            a_i = A[int(constr_index),:]
            nonzero_a_ij = np.nonzero(a_i[:n])[0]
            if len(nonzero_a_ij) > 0:
                j = nonzero_a_ij[0] # choose index of arbitrary nonzero a_ij
                # pivot with entering j and leaving i
                B = list(set(B).difference(set([i])).union(set([j])))
                B.sort()
                T = aux_lp.get_tableau(B)
                A = T[1:,1:-1]
                b = np.array([T[1:,-1]]).transpose()
                x = np.zeros((len(x),1))
                x[B,0] = b[:,0]
            else:
                # delete constraint
                A = np.delete(A, constr_index, 0)
                b = np.delete(b, constr_index, 0)

            # delete u_i
            A = np.delete(A, i, 1)
            c = np.delete(c, i, 0)
            index_in_basis = np.zeros(len(x))
            index_in_basis[B] = 1
            index_in_basis = np.delete(index_in_basis, i, 0)
            B = list(np.nonzero(index_in_basis)[0])
            x = np.delete(x, i, 0)
        return x,B

def simplex_iteration(lp: LP,
                      x: np.ndarray,
                      B: List[int],
                      pivot_rule: str = 'bland',
                      feasibility_tol: float = 1e-7
                      ) -> Tuple[np.ndarray, List[int], float, bool]:
    """Execute a single iteration of the revised simplex method.

    Let x be the initial basic feasible solution with corresponding basis B.
    Use a primal feasibility tolerance of feasibility_tol (with default vlaue
    of 1e-7). Do one iteration of the revised simplex method using the given
    pivot rule. Implemented pivot rules include:

    Entering variable:

        - 'bland' or 'min_index': minimum index
        - 'dantzig' or 'max_reduced_cost': most positive reduced cost
        - 'greatest_ascent': most positive (minimum ratio) x (reduced cost)
        - 'manual_select': user selects among possible entering indices

    Leaving variable:

        - (All): minimum (positive) ratio (minimum index to tie break)

    Args:
        lp (LP): LP on which the simplex iteration is being done.
        x (np.ndarray): Initial basic feasible solution.
        B (List(int)): Basis corresponding to basic feasible solution x.
        pivot_rule (str): Pivot rule to be used. 'bland' by default.
        feasibility_tol (float): Primal feasibility tolerance (1e-7 default).

    Returns:
        Tuple:

        - np.ndarray: New basic feasible solution.
        - List[int]: Basis corresponding to the new basic feasible solution.
        - float: Objective value of the new basic feasible solution.
        - bool: An idication of optimality. True if optimal. False otherwise.

    Raises:
        ValueError: Invalid pivot rule. Select from (list).
        ValueError: x should have shape (n+m,1) but was ().

    """
    pivot_rules = ['bland','min_index','dantzig','max_reduced_cost',
                   'greatest_ascent','manual_select']
    if pivot_rule not in pivot_rules:
        raise ValueError('Invalid pivot rule. Select from ' + str(pivot_rules))
    n,m,A,b,c = equality_form(lp).get_coefficients()
    if not x.shape == (n, 1):
        raise ValueError('x should have shape (' + str(n) + ',1) '
                         + 'but was ' + str(x.shape))
    if not np.allclose(x, lp.get_basic_feasible_sol(B), atol=feasibility_tol):
        raise ValueError('The basis ' + str(B) + ' corresponds to a different '
                         + 'basic feasible solution.')

    N = list(set(range(n)) - set(B))
    y = solve(A[:,B].transpose(), c[B,:])
    red_costs = c - np.dot(y.transpose(),A).transpose()
    entering = {k: red_costs[k] for k in N if red_costs[k] > 0}
    if len(entering) == 0:
        current_value = float(np.dot(c.transpose(), x))
        return x,B,current_value,True
    else:
        if pivot_rule == 'greatest_ascent':
            eligible = {}
            for k in entering:
                d = np.zeros((1,n))
                d[:,B] = solve(A[:,B], A[:,k])
                ratios = {i: x[i]/d[0][i] for i in B if d[0][i] > 0}
                if len(ratios) == 0:
                    raise UnboundedLinearProgram('This LP is unbounded')
                t = min(ratios.values())
                r_pos = [r for r in ratios if ratios[r] == t]
                r = min(r_pos)
                t = ratios[r]
                eligible[(t*red_costs[k])[0]] = [k,r,t,d]
            k,r,t,d = eligible[max(eligible.keys())]
        else:
            user_input = None
            if pivot_rule == 'manual_select':
                user_options = [i + 1 for i in entering.keys()]
                user_input = int(input('Pick one of ' + str(user_options))) - 1
            k = {'bland': min(entering.keys()),
                 'min_index': min(entering.keys()),
                 'dantzig': max(entering, key=entering.get),
                 'max_reduced_cost': max(entering, key=entering.get),
                 'manual_select': user_input}[pivot_rule]
            d = np.zeros((1,n))
            d[:,B] = solve(A[:,B], A[:,k])
            ratios = {i: x[i]/d[0][i] for i in B if d[0][i] > 0}
            if len(ratios) == 0:
                raise UnboundedLinearProgram('This LP is unbounded')
            t = min(ratios.values())
            r_pos = [r for r in ratios if ratios[r] == t]
            r = min(r_pos)
            t = ratios[r]
        # update
        x[k] = t
        x[B,:] = x[B,:] - t*(d[:,B].transpose())
        B.append(k)
        B.remove(r)
        N.append(r)
        N.remove(k)
        current_value = float(np.dot(c.transpose(), x))
        return x,B,current_value,False


def simplex(lp: LP,
            pivot_rule: str = 'bland',
            initial_solution: np.ndarray = None,
            iteration_limit: int = None,
            feasibility_tol: float = 1e-7
            ) -> Tuple[List[np.ndarray], List[List[int]], float, bool]:
    """Execute the revised simplex method on the given LP.

    Execute the revised simplex method on the given LP using the specified
    pivot rule. If a valid initial basic feasible solution is given, use it as
    the initial bfs. Otherwise, ignore it. If an iteration limit is given,
    terminate if the specified limit is reached. Output the current solution
    and indicate the solution may not be optimal. Use a primal feasibility
    tolerance of feasibility_tol (with default vlaue of 1e-7).

    PIVOT RULES

    Entering variable:

        - 'bland' or 'min_index': minimum index
        - 'dantzig' or 'max_reduced_cost': most positive reduced cost
        - 'greatest_ascent': most positive (minimum ratio) x (reduced cost)
        - 'manual_select': user selects among possible entering indices

    Leaving variable:

        - (All): minimum (positive) ratio (minimum index to tie break)

    Args:
        lp (LP): LP on which to run simplex
        pivot_rule (str): Pivot rule to be used. 'bland' by default.
        initial_solution (np.ndarray): Initial bfs. None by default.
        iteration_limit (int): Simplex iteration limit. None by default.
        feasibility_tol (float): Primal feasibility tolerance (1e-7 default).

    Return:
        Tuple:

        - List[np.ndarray]: Basic feasible solutions at each simplex iteration.
        - List[List[int]]: Corresponding bases at each simplex iteration.
        - float: The current objective value.
        - bool: True if the current objective value is known to be optimal.

    Raises:
        ValueError: Invalid pivot rule. Select from (list).
        ValueError: Iteration limit must be strictly positive.
        ValueError: initial_solution should have shape (n,1) but was ().
    """
    pivot_rules = ['bland','min_index','dantzig','max_reduced_cost',
                   'greatest_ascent','manual_select']
    if pivot_rule not in pivot_rules:
        raise ValueError('Invalid pivot rule. Select from ' + str(pivot_rules))
    if iteration_limit is not None and iteration_limit <= 0:
        raise ValueError('Iteration limit must be strictly positive.')

    n,m,A,b,c = equality_form(lp).get_coefficients()

    x,B = phase_one(lp, pivot_rule=pivot_rule)

    if initial_solution is not None:
        if not initial_solution.shape == (n, 1):
            raise ValueError('initial_solution should have shape (' + str(n)
                             + ',1) but was ' + str(initial_solution.shape))
        x_B = initial_solution
        if (np.allclose(np.dot(A,x_B), b, atol=feasibility_tol) and
                all(x_B >= np.zeros((n,1)) - feasibility_tol) and
                len(np.nonzero(x_B)[0]) <= m):
            x = x_B
            B = list(np.nonzero(x_B)[0])
            N = list(set(range(n)) - set(B))
            while len(B) < m:  # if initial solution is degenerate
                B.append(N.pop())
        else:
            print('Initial solution ignored.')

    path = [np.copy(x)]
    bases = [list.copy(B)]
    current_value = float(np.dot(c.transpose(), x))
    optimal = False

    if iteration_limit is not None:
        lim = iteration_limit
    while(not optimal):
        x,B,value,opt = simplex_iteration(lp,x,B,pivot_rule,feasibility_tol)
        current_value = value
        if opt:
            optimal = True
        else:
            path.append(np.copy(x))
            bases.append(list.copy(B))
        if iteration_limit is not None:
            lim = lim - 1
        if iteration_limit is not None and lim == 0:
            break

    return path, bases, current_value, optimal