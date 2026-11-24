"""Full-vector FEM mode solver (with PML) for elliptical-hole PCFs.

Solves curl([s]^-1 curl E) - k0^2 n^2 [s] E = 0 (Eq. 1 of Ademgil & Haxha, Sensors 2015)
with mixed elements: 2nd-order Nedelec (transverse E) + quadratic Lagrange (Ez), on
curved (isoparametric) triangles.  The fibre has two mirror planes, so one quarter is
solved; the wall condition selects the polarisation:
    x-pol (HE11x): PEC on x=0, PMC on y=0        y-pol: PMC on x=0, PEC on y=0
All lengths in micrometres.
"""
from dataclasses import dataclass, replace
import os, tempfile
import numpy as np
import gmsh, meshio
import scipy.sparse as sp
import scipy.sparse.linalg as spl
from skfem import (Basis, BilinearForm, Functional, ElementTriN2, ElementTriP2,
                   MeshTri, MeshTri2)
from skfem.helpers import dot, grad

SILICA, AIR, ANALYTE, PML = 1, 2, 3, 4


@dataclass(frozen=True)
class Design:
    kind: str = "V"          # "V" or "H"
    eta: float = 0.7         # db/da
    da: float = 1.0          # cladding hole major SEMI-axis
    ds: float = 0.4          # core hole major SEMI-axis
    dc: float = 0.2          # core hole minor SEMI-axis
    pitch: float = 2.4
    pitch_core: float = 1.0
    rings: int = 3
    gap: float = 1.0         # silica between outermost hole and PML
    t_pml: float = 2.5
    s_pml: float = 6.0       # peak of the quadratic PML conductivity profile
    h: float = 1.0           # mesh scale factor (smaller = finer)

    def holes(self):
        """(x, y, rx, ry, tag) for all holes with centre in the closed first quadrant."""
        a, b = self.da, self.da * self.eta
        cl = (b, a) if self.kind == "V" else (a, b)
        co = (self.dc, self.ds) if self.kind == "V" else (self.ds, self.dc)
        out = []
        N, L, Lc = self.rings, self.pitch, self.pitch_core
        for i in range(-N, N + 1):
            for j in range(-N, N + 1):
                if max(abs(i), abs(j), abs(i + j)) > N or (i == 0 and j == 0):
                    continue
                out.append((L * (i + j / 2), L * j * np.sqrt(3) / 2, *cl, AIR))
        out.append((0, 0, *co, ANALYTE))
        for k in range(6):      # nearest neighbours on the +/-y axis, as in Fig. 1
            t = np.pi / 2 + k * np.pi / 3
            out.append((Lc * np.cos(t), Lc * np.sin(t), *co, ANALYTE))
        return out

    def window(self):
        hs = self.holes()
        return (max(x + rx for x, y, rx, ry, t in hs) + self.gap,
                max(y + ry for x, y, rx, ry, t in hs) + self.gap)


_cache = {}


def curved_mesh(p, t6):
    """Quadratic skfem mesh from gmsh triangle6 data.

    The Nedelec element needs vertex indices sorted within each element (consistent edge
    orientation); from_meshio does not do that for quadratic meshes, so it is done here.
    """
    used, inv = np.unique(t6[:3], return_inverse=True)
    t = inv.reshape(3, -1)
    M = MeshTri2.from_mesh(MeshTri(np.ascontiguousarray(p[:, used]), np.ascontiguousarray(t), sort_t=True))
    assert (np.diff(M.t, axis=0) > 0).all()
    mid = {}
    for a, b, k in ((0, 1, 3), (1, 2, 4), (2, 0, 5)):
        for i, j, q in zip(t[a], t[b], t6[k]):
            mid[(min(i, j), max(i, j))] = q
    loc = M.doflocs.copy()
    fd = M.dofs.facet_dofs[0]
    for f, (i, j) in enumerate(M.facets.T):
        loc[:, fd[f]] = p[:, mid[(min(i, j), max(i, j))]]
    return replace(M, doflocs=loc)


def make_mesh(d: Design):
    if d in _cache:
        return _cache[d]
    X, Y = d.window()
    T = d.t_pml
    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        g = gmsh.model.occ
        boxes = [g.addRectangle(0, 0, 0, X, Y), g.addRectangle(X, 0, 0, T, Y),
                 g.addRectangle(0, Y, 0, X, T), g.addRectangle(X, Y, 0, T, T)]
        els = []
        hs = [q for q in d.holes() if q[0] > -1e-9 and q[1] > -1e-9
              or (q[0] + q[2] > 1e-9 and q[1] + q[3] > 1e-9)]
        for x, y, rx, ry, tag in hs:
            e = (g.addEllipse(x, y, 0, rx, ry) if rx >= ry else
                 g.addEllipse(x, y, 0, ry, rx, zAxis=[0, 0, 1], xAxis=[0, 1, 0]))
            els.append(g.addPlaneSurface([g.addCurveLoop([e])]))
        quarter = g.addRectangle(0, 0, 0, X, Y)
        els2 = g.intersect([(2, e) for e in els], [(2, quarter)])[0]
        g.fragment([(2, b) for b in boxes], els2)
        g.synchronize()
        groups = {SILICA: [], AIR: [], ANALYTE: [], PML: []}
        for _, s in gmsh.model.getEntities(2):
            x0, y0, _, x1, y1, _ = gmsh.model.getBoundingBox(2, s)
            # a hole is recognised by an interior point
            p = gmsh.model.occ.getCenterOfMass(2, s)
            if p[0] > X or p[1] > Y:
                groups[PML].append(s); continue
            tag = SILICA
            for x, y, rx, ry, t in hs:
                inside = ((p[0]-x)/rx)**2 + ((p[1]-y)/ry)**2 < 1
                fits = x1 <= x+rx+1e-3 and x0 >= x-rx-1e-3 and y1 <= y+ry+1e-3 and y0 >= y-ry-1e-3
                if inside and fits:
                    tag = t
            groups[tag].append(s)
        for t, ss in groups.items():
            gmsh.model.addPhysicalGroup(2, ss, t)
        # mesh size: fine in core, coarser outwards
        f = gmsh.model.mesh.field
        f.add("MathEval", 1)
        f.setString(1, "F", f"{d.h}*(0.10+0.03*Sqrt(x*x+y*y))")
        f.setAsBackgroundMesh(1)
        for o in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
            gmsh.option.setNumber("Mesh." + o, 0)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.HighOrderOptimize", 2)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        fn = tempfile.mktemp(suffix=".msh")
        gmsh.write(fn)
    finally:
        gmsh.finalize()
    mm = meshio.read(fn); os.remove(fn)
    cells = np.vstack([c.data for c in mm.cells if c.type == "triangle6"])
    tags = np.concatenate([mm.cell_data["gmsh:physical"][k]
                           for k, c in enumerate(mm.cells) if c.type == "triangle6"])
    m = curved_mesh(mm.points[:, :2].T, cells.T)
    assert m.t.shape[1] == len(tags)
    _cache[d] = (m, tags)
    return _cache[d]


@dataclass
class Mode:
    neff: complex
    loss: float          # dB/m, from the energy identity (no cancellation)
    f: float             # power fraction in analyte (0-1)
    core: float          # power fraction within 2.0 um of the centre
    x: np.ndarray
    basis: Basis
    beta2: complex
    naive: float = 0.0   # loss straight from the complex eigenvalue (round-off limited)
    def r(self, na):
        return 100 * na / self.neff.real * self.f


def solve(d: Design, lam, n_analyte, pol="x", guess=None, nev=12, n_si=1.45, n_air=1.0):
    m, tags = make_mesh(d)
    X, Y = d.window()
    k0 = 2 * np.pi / lam
    basis = Basis(m, ElementTriN2() * ElementTriP2(), intorder=6)
    n = np.select([tags == SILICA, tags == AIR, tags == ANALYTE, tags == PML],
                  [n_si, n_air, n_analyte, n_si])
    q = basis.global_coordinates().value
    xq, yq = q[0], q[1]
    eps = (n ** 2)[:, None] * np.ones_like(xq)
    sx = 1 - 1j * d.s_pml * (np.maximum(xq - X, 0) / d.t_pml) ** 2
    sy = 1 - 1j * d.s_pml * (np.maximum(yq - Y, 0) / d.t_pml) ** 2
    px, py, pz = sy / sx, sx / sy, sx * sy      # PML tensor, for eps and mu alike

    @BilinearForm(dtype=complex)
    def aform(e, ez, w, wz, _):
        return e.curl * w.curl / pz - k0**2 * eps * (px*e[0]*w[0] + py*e[1]*w[1])

    @BilinearForm(dtype=complex)
    def bform(e, ez, w, wz, _):
        ge, gw = grad(ez), grad(wz)
        return (px * (ge[0]+e[0]) * (gw[0]+w[0]) + py * (ge[1]+e[1]) * (gw[1]+w[1])
                - k0**2 * eps * pz * ez * wz)

    A = aform.assemble(basis).tocsr(); B = bform.assemble(basis).tocsr()
    tol = 1e-6
    wall = (lambda p: p[0] < tol) if pol == "x" else (lambda p: p[1] < tol)
    Xo, Yo = X + d.t_pml, Y + d.t_pml
    facets = np.unique(np.concatenate([m.facets_satisfying(wall, boundaries_only=True),
        m.facets_satisfying(lambda p: p[0] > Xo - tol, boundaries_only=True),
        m.facets_satisfying(lambda p: p[1] > Yo - tol, boundaries_only=True)]))
    D = basis.get_dofs(facets).all()
    I = np.setdiff1d(np.arange(basis.N), D)
    Ai, Bi = A[I][:, I].tocsc(), B[I][:, I].tocsc()
    if guess is None:
        guess = 1.41
    sigma = -(k0 * guess) ** 2
    lu = spl.splu((Ai - sigma * Bi).tocsc(), permc_spec="COLAMD")
    op = spl.LinearOperator(Ai.shape, matvec=lambda v: lu.solve(Bi @ v), dtype=complex)
    v0 = np.random.default_rng(0).standard_normal(len(I)).astype(complex)
    mu, V = spl.eigs(op, k=nev, which="LM", v0=v0, tol=1e-13)
    out = []
    an = (tags == ANALYTE)[:, None] * np.ones_like(xq)
    inner = (tags != PML)[:, None] * np.ones_like(xq)
    corem = (xq**2 + yq**2 < 4.0).astype(float)
    Aim, Bim = Ai.imag.tocsr(), Bi.imag.tocsr()
    Bre = Bi.real.tocsr()
    for k in range(nev):
        lam_e = sigma + 1 / mu[k]
        v = V[:, k]
        for _ in range(2):                      # inverse iteration: clean the tiny tail
            v = lu.solve(Bi @ v); v /= np.linalg.norm(v)
        lam_e = (v @ (Ai @ v)) / (v @ (Bi @ v))
        # energy identity: Im part comes only from PML entries
        naive = 8.685889638e6 * k0 * abs((np.sqrt(-lam_e) / k0).imag)
        lr = lam_e.real
        num = (np.vdot(v, Aim @ v) - lr * np.vdot(v, Bim @ v)).real
        li = num / np.vdot(v, Bre @ v).real
        beta2 = -lr - 1j * li
        neff = np.sqrt(beta2) / k0
        full = np.zeros(basis.N, complex); full[I] = v
        e, ez = basis.interpolate(full)
        gz = grad(ez)
        S = (e[0]*np.conj(gz[0]+e[0]) + e[1]*np.conj(gz[1]+e[1])).real * basis.dx
        tot = (S*inner).sum()
        out.append(Mode(neff, 8.685889638 * k0 * 1e6 * abs(neff.imag),
                        (S*an).sum()/tot, (S*corem).sum()/tot, full, basis, beta2, naive))
    return out


def fundamental(d, lam, na, pol="x", guess=None, nev=12, mincore=0.3, **kw):
    """LP01 mode = most core-confined mode of the symmetry class."""
    ms = solve(d, lam, na, pol, guess, nev, **kw)
    return max(ms, key=lambda q: q.core)
