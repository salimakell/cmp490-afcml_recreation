"""Three-stage pipeline on the paper's CSV format.

Stage 1  classify test by randomized variables (rule based)
Stage 2  K-means++ (k=4) on the 9 Fig. 4 columns (standardized)
Stage 3  one decision tree per cluster predicting the CSV "Coverage" label
Labels (from the training simulation log):
  B        Fig. 4 rule  (granted & HBUSREQ & HWRITE, same row)
  A_same   grant held during this row (depends on the PREVIOUS row)
  A_next   grant caused by this row (= grant in the next row)
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tb"))
import stimulus as S  # noqa: E402

K, SEED = 4, 0
VARS = [c for c in S.COLS]   # stage 1: the randomized variables define the class


def classify_test(r):
    return r["test"]


def labels(log, kind):
    A = [e[2] for e in log]
    B = [e[3] for e in log]
    if kind == "B":
        return np.array(B)
    if kind == "A_same":
        return np.array(A)
    if kind == "A_next":
        return np.array(A[1:] + [0])
    raise ValueError(kind)


def train(pool, log, kind, seed=SEED):
    y = labels(log, kind)
    X = np.array([S.features(r) for r in pool], float)
    sc = StandardScaler().fit(X)
    km = KMeans(K, init="k-means++", n_init=10, random_state=seed).fit(sc.transform(X))
    trees, yt, yp = {}, [], []
    for c in range(K):
        ci = np.where(km.labels_ == c)[0]
        Xc, yc = X[ci], y[ci]
        if len(set(yc)) < 2:
            trees[c] = ("const", float(yc.mean()))
            yt += list(yc); yp += [int(yc[0])] * len(yc)
            continue
        Xtr, Xte, ytr, yte = train_test_split(Xc, yc, test_size=0.25, stratify=yc, random_state=seed)
        dt = DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, class_weight="balanced",
                                    random_state=seed).fit(Xtr, ytr)
        p = dt.predict(Xte)
        yt += list(yte); yp += list(p)
        trees[c] = ("dt", DecisionTreeClassifier(max_depth=4, min_samples_leaf=50,
                                                 class_weight="balanced", random_state=seed).fit(Xc, yc))
    rep = {"label": kind, "pos_rate": float(y.mean()),
           "heldout_acc": float(accuracy_score(yt, yp)),
           "heldout_balanced_acc": float(balanced_accuracy_score(yt, yp)),
           "always_zero_acc": float(1 - np.mean(yt)),
           "cluster_sizes": np.bincount(km.labels_).tolist()}
    return {"scaler": sc, "kmeans": km, "trees": trees}, rep


def apply(model, pool, outdir):
    os.makedirs(outdir, exist_ok=True)
    X = np.array([S.features(r) for r in pool], float)
    cl = model["kmeans"].predict(model["scaler"].transform(X))
    buckets, tail = defaultdict(list), []
    for r, x, c in zip(pool, X, cl):
        kind, t = model["trees"][int(c)]
        p = t if kind == "const" else float(t.predict_proba([x])[0][list(t.classes_).index(1)])
        (buckets[int(c)] if p >= 0.5 else tail).append((p, r))
    order = sorted(range(K), key=lambda c: -np.mean([p for p, _ in buckets[c]]) if buckets[c] else 0)
    files = []
    for i, c in enumerate(order):
        f = os.path.join(outdir, f"c{i}.json")
        S.save([r for p, r in sorted(buckets[c], key=lambda z: -z[0])], f)
        files.append(f)
    f = os.path.join(outdir, "tail.json")
    S.save([r for _, r in tail], f)
    return files + [f]
