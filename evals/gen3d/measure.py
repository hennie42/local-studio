"""Mesh checks and shape accuracy of a generated mesh against its ground truth.

python measure.py [--save-aligned DIR] [--up +z] <gt.glb|.gltf> <generated.glb|.obj> [...]  -> one JSON line per generated mesh

Both meshes are centred and scaled to a bounding-box diagonal of 1. The generated mesh is aligned to the ground
truth by trying the 24 axis-aligned rotations and the 24 principal-axis matchings, each refined by rigid ICP, keeping
the best (generators output tilted, camera-relative frames). With --up (the generated mesh's up axis in glTF
coordinates; ground truth is +y) the search is only 24 turns about the up axis, so near-cubic shapes cannot be tipped
over. --save-aligned writes the transform that moves each generated
mesh into the ground truth's frame (<name>.align.json), for side-by-side renders. Reported:
chamfer (mean of both directions' mean nearest distance, in diagonals; lower is better), F-score at 1, 2 and 5 %
of the diagonal (higher is better), plus triangle count, watertight, bodies and non-manifold edges."""
import itertools
import json
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

N = 20000
rng = np.random.default_rng(0)


def load(path):
    m = trimesh.load(path, force="mesh", process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)  # geometry only: UV seams must not split bodies
    return m


def frame(m):
    lo, hi = m.bounds
    return (lo + hi) / 2, np.linalg.norm(hi - lo)


def normalised_points(m):
    pts, _ = trimesh.sample.sample_surface(m, N, seed=0)
    c, d = frame(m)
    return (pts - c) / d


def pca(p):
    _, vecs = np.linalg.eigh(np.cov((p - p.mean(0)).T))
    return vecs[:, ::-1]  # columns = principal axes, largest first


def rotations24():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            r = np.zeros((3, 3))
            for i, (p, s) in enumerate(zip(perm, signs)):
                r[i, p] = s
            if np.isclose(np.linalg.det(r), 1):
                out.append(r)
    return out


def scores(a, b):
    da, _ = cKDTree(b).query(a)
    db, _ = cKDTree(a).query(b)
    res = {"chamfer": float((da.mean() + db.mean()) / 2)}
    for tau in (0.01, 0.02, 0.05):
        p, r = (da < tau).mean(), (db < tau).mean()
        res[f"f@{int(tau * 100)}%"] = float(2 * p * r / (p + r)) if p + r else 0.0
    return res


def upright_starts(up):
    """Rotations taking the generated mesh's up axis to +y, then turned about +y in 15 degree steps."""
    sign, axis = (-1 if up[0] == "-" else 1), "xyz".index(up[-1])
    u = np.zeros(3); u[axis] = sign
    to_y = trimesh.geometry.align_vectors(u, [0, 1, 0])[:3, :3]
    return [trimesh.transformations.rotation_matrix(np.radians(a), [0, 1, 0])[:3, :3] @ to_y for a in range(0, 360, 15)]


def align(gen, gt, up=None):
    """Returns (4x4 transform on normalised gen points, aligned points)."""
    if up:
        starts = upright_starts(up)
    else:
        pg, pt = pca(gen), pca(gt)
        starts = list(rotations24()) + [pt @ r @ pg.T for r in rotations24()]
    best = None
    for r in starts:
        start = np.eye(4); start[:3, :3] = r
        mat, moved, cost = trimesh.registration.icp(gen, gt, initial=start, max_iterations=40, scale=False)
        if best is None or cost < best[2]:
            best = (mat, moved, cost)
    return best[0], best[1]


def bodies(m):
    """Connected components over shared edges (m.split() copies every piece: > 12 GB on a TRELLIS.2 mesh)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    adj = m.face_adjacency
    n = len(m.faces)
    return int(connected_components(coo_matrix((np.ones(len(adj)), (adj[:, 0], adj[:, 1])), shape=(n, n)))[0])


def stats(m):
    edges = m.edges_sorted
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return {"tris": int(len(m.faces)), "watertight": bool(m.is_watertight),
            "bodies": bodies(m), "nonmanifold_edges": int((counts > 2).sum())}


args = sys.argv[1:]
save_dir = up = None
while args[0].startswith("--"):
    if args[0] == "--save-aligned":
        save_dir = args[1]
    elif args[0] == "--up":
        up = args[1]
    args = args[2:]
gt = load(args[0])
gt_pts = normalised_points(gt)
for path in args[1:]:
    m = load(path)
    mat, gen_pts = align(normalised_points(m), gt_pts, up)
    print(json.dumps({"mesh": path, **stats(m), **scores(gen_pts, gt_pts)}), flush=True)
    if save_dir:
        import os
        (c, d), (gc, gd) = frame(m), frame(gt)
        to_unit = np.eye(4); to_unit[:3, :3] /= d; to_unit[:3, 3] = -c / d
        to_gt = np.eye(4); to_gt[:3, :3] *= gd; to_gt[:3, 3] = gc
        name = path.replace("/", "_").rsplit(".", 1)[0] + ".align.json"
        with open(os.path.join(save_dir, name), "w") as f:  # glTF (Y-up) frame; render_views.py --align applies it
            json.dump((to_gt @ mat @ to_unit).tolist(), f)
