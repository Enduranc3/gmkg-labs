"""Чисельні методи: інтегрування та похідні."""


def simpson(f, lo, hi, n=1000):
    """Інтеграл f на [lo, hi] методом Сімпсона (n - парна кількість відрізків)."""
    if n % 2:
        n += 1
    h = (hi - lo) / n
    total = f(lo) + f(hi)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(lo + i * h)
    return total * h / 3


def derivative(f, x, h=1e-5):
    """Центральна різниця: f'(x) ≈ (f(x + h) - f(x - h)) / 2h."""
    return (f(x + h) - f(x - h)) / (2 * h)
