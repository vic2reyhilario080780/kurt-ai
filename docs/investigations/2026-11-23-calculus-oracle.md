# Independent mathematical oracle

This oracle is separate from the baseline inference prompt and application code.
Write L=log n, N=sqrt(n), γ=Euler's constant, and
H(t)=∫₀ᵗ(1−exp(−v))/v dv, with H(0)=0.

The exact constants are

    a = 2√π
    b = −1/4
    c = log 2 − 1 − γ/2
    d = −2 − γ + γ log 2 − γ²/4 − 5π²/24
    e = √π
    f = 0.

In fact Rₙ=−1/(2n²)+O(n^(−5/2)), so the requested limit is **0**.
The proposed logarithmic bound is valid but **not sharp**: the remainder is
Θ(n⁻²), and n²Rₙ→−1/2. Here and below n is real, n≥2.

## Derivation with convergence checks

All original integrands are nonnegative and bounded on the cube. Tonelli
permits integrating x,y first; substitution gives

    ∫₀¹∫₀¹ exp(−txy) dx dy = H(t)/t,
    Iₙ = (Aₙ−Bₙ+Cₙ)/n,
    Aₙ = ∫₀¹ H(nz²)/z² dz,
    Bₙ = ∫₀¹ H(nz²)/z dz,
    Cₙ = ∫₀¹ H(nz²)/(1+z) dz.

The partial fraction identity is applied with H retained in every term.
Since 0≤H(t)≤t, these three integrals converge at zero. No divergent
integrals have been subtracted. Integration by parts at ε>0 followed by
ε↓0 is valid because H(nε²)/ε≤nε→0. It gives

    Aₙ = 2√π N erf(N) − 2 + 2 exp(−n) − H(n).

For t>0 set E₁(t)=∫ₜ∞ exp(−v)/v dv. Differentiating, and matching the
limit at zero, gives H(t)=γ+log t+E₁(t). In particular the sign in front
of Ei(−t)=−E₁(t) is negative, not positive. Therefore

    Aₙ = 2√π N − L − γ − 2 + δA,
    δA = −2√π N erfc(N) + 2 exp(−n) − E₁(n),
    |δA| ≤ 5 exp(−n).

Here erfc(N)≤exp(−n)/(√π N) and E₁(n)≤exp(−n)/n.

Tonelli applied to H(t)=∫₀ᵗ exp(−v) log(t/v) dv yields

    Bₙ = 1/4 ∫₀ⁿ exp(−v) [log(n/v)]² dv
       = L²/4 + γL/2 + γ²/4 + π²/24 − δB,
    δB = 1/4 ∫ₙ∞ exp(−v) [log(v/n)]² dv,
    0≤δB≤exp(−n)/(2n²).

The last bound uses log(v/n)≤(v−n)/n. The two logarithmic Gamma moments
are ∫₀∞e⁻ᵛ log v dv=−γ and ∫₀∞e⁻ᵛ(log v)²dv=γ²+π²/6.
For completeness these follow by twice differentiating the Gamma integral
near s=1 (domination by e⁻ᵛ(v^(−1/2)+v^(1/2))(1+|log v|²)), and
the Euler product giving (log Γ)'(1)=−γ, (log Γ)''(1)=π²/6.
These derivatives are intermediate identities, not unevaluated constants.

Also

    Cₙ = (L+γ) log 2 − π²/6 + Eₙ,
    Eₙ = N⁻¹ ∫₀ᴺ E₁(u²)/(1+u/N) du.

Here ∫₀¹ log z/(1+z) dz=−π²/12. To justify its geometric-series
evaluation, the integrated absolute terms sum to ∑ₖ≥0 1/(k+1)²<∞;
thus Fubini applies. The alternating reciprocal-square sum is π²/12.
Every log term is integrable in this decomposition of Cₙ.

The nonnegative representation E₁(u²)=∫₁∞exp(−tu²)/t dt and Tonelli give

    Mₖ = ∫₀∞ uᵏ E₁(u²) du = Γ((k+1)/2)/(k+1),   k>−1,
    M₀=√π, M₁=1/2, M₂=√π/6.

Use the **exact** identity 1/(1+x)=1−x+x²/(1+x), not a nonuniform
large-argument series. On extending the u-integral to infinity one gets

    Eₙ = √π/N − 1/(2N²) + Qₙ/N³ − Tₙ,
    Qₙ = ∫₀∞ u² E₁(u²)/(1+u/N) du,
    0≤Qₙ≤M₂,
    Tₙ = N⁻¹ ∫ᴺ∞ E₁(u²)/(1+u/N) du,
    0≤Tₙ≤exp(−n)/(2n²).

For the tail use E₁(u²)≤exp(−u²)/u²≤exp(−u²)/N² and
∫ᴺ∞exp(−u²)du≤exp(−n)/(2N). All integrals here converge, including at
zero (E₁(u²)=O(1+|log u|)). No infinite asymptotic series is integrated.

Combining the three expressions proves the constants above and the exact
remainder representation

    Rₙ = −1/(2n²) + Qₙ/n^(5/2) + (δA+δB−Tₙ)/n.

In particular |Rₙ|≤7/n²≤7(1+log n)/n² for **all** n≥2. This follows
from n exp(−n)≤1, |δA|≤5exp(−n), Qₙ≤√π/6, and the two tail bounds.
Multiplication by n² shows n²Rₙ→−1/2, since Qₙ/√n→0 and all exponential
terms vanish. Division by log n gives the requested limit zero. If a
limit inside Qₙ is desired, domination by u²E₁(u²) gives Qₙ→M₂, but it
is unnecessary for the limit asked for.

## Independent decisive checks and grading rubric

On z∈[0,1/√n], exp(−nxyz²)≥e⁻¹ and (1+z)⁻¹≥1/2, giving
Iₙ≥1/(2e√n). Thus a=0 with the requested smaller-order remainder is
impossible. Tonelli also gives the exact leading coefficient independently:
∫₀∞∫₀¹∫₀¹ exp(−xyu²) dx dy du=2√π; monotone or dominated convergence
after z=u/√n gives √n Iₙ→2√π.

Grade separately: (1) leading term, (2) all six coefficients matched to the
requested powers/logs, (3) convergence and justified interchanges,
(4) uniform remainder proof, (5) exact limit and sharpness. Any a=0,
finite value assigned to ∫₀¹z⁻²/(1+z)dz, or large-argument E₁ expansion
used down to zero fails independently. These checks must not be injected
into baseline inference.

Fresh control problem: Jₙ=∫₀¹ x/(1+nx²)dx. Exactly Jₙ=log(1+n)/(2n).
Its expansion is L/(2n)+1/(2n²)−1/(4n³)+O(n⁻⁴); the error after these
three terms is between 0 and 1/(6n⁴), by the alternating log series for
1/n≤1/2. The corresponding n³ scaled difference limit is −1/4.
