import random, math

def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-30: d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12: break
    return h

def _betainc(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b

def _beta_ppf(p, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _betainc(a, b, mid) < p: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

def clopper_pearson(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else _beta_ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return lo * 100.0, hi * 100.0

random.seed(42)
trials = []

# G1: Normal baseline (100 negativos)
for _ in range(100):
    trials.append((False, False, random.uniform(0.0, 0.25), random.uniform(0.0, 0.20), 999.0))

# G2: Perturbação isolada de 1 domínio (100 negativos)
for i in range(100):
    if i < 50:
        trials.append((False, False, random.uniform(0.65, 0.85), random.uniform(0.0, 0.20), 999.0))
    else:
        trials.append((False, False, random.uniform(0.0, 0.20), random.uniform(0.65, 0.85), 999.0))

# G3: Ataques híbridos coordenados (100 positivos híbridos)
for _ in range(100):
    dt = random.uniform(0.5, 22.0)
    c_vis = random.uniform(0.75, 0.98) if random.random() > 0.04 else random.uniform(0.30, 0.48)
    c_net = random.uniform(0.75, 0.99)
    trials.append((True, True, c_vis, c_net, dt))

# G4: Eventos benignos coincidentes nos 2 domínios (100 negativos difíceis)
for _ in range(100):
    dt = random.uniform(1.0, 28.0)
    trials.append((False, False, random.uniform(0.51, 0.68), random.uniform(0.51, 0.66), dt))

# G5: Ataques unimodais reais (100 positivos: 50 só físicos + 50 só de rede)
for i in range(100):
    if i < 50:
        trials.append((True, False, random.uniform(0.78, 0.97), random.uniform(0.0, 0.20), 999.0))
    else:
        trials.append((True, False, random.uniform(0.0, 0.20), random.uniform(0.78, 0.98), 999.0))

def eval_detector(name, predict_fn):
    TP = FP = TN = FN = 0
    for is_att, _, cv, cn, dt in trials:
        pred = predict_fn(cv, cn, dt)
        if is_att and pred: TP += 1
        elif not is_att and pred: FP += 1
        elif not is_att and not pred: TN += 1
        elif is_att and not pred: FN += 1
    prec = TP / (TP + FP) * 100 if (TP + FP) else 0
    rec  = TP / (TP + FN) * 100 if (TP + FN) else 0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    fpr  = FP / (FP + TN) * 100 if (FP + TN) else 0
    fpr_lo, fpr_hi = clopper_pearson(FP, FP + TN)
    rec_lo, rec_hi = clopper_pearson(TP, TP + FN)
    print(f"{name:34s} | Prec:{prec:5.1f}% | Rec:{rec:5.1f}% [{rec_lo:4.1f}-{rec_hi:4.1f}] | F1:{f1:5.1f}% | FPR:{fpr:5.1f}% [{fpr_lo:4.1f}-{fpr_hi:4.1f}]")

print("=== TABELA IV: COMPARAÇÃO COM BASELINES E G4/G5 (N=500) ===")
eval_detector("Vision Only (th>=0.5)",             lambda cv, cn, dt: cv >= 0.5)
eval_detector("Network Only (th>=0.5)",            lambda cv, cn, dt: cn >= 0.5)
eval_detector("OR Fusion (V or N)",                lambda cv, cn, dt: (cv >= 0.5) or (cn >= 0.5))
eval_detector("Weighted Sum (0.5V+0.5N>=0.65)",    lambda cv, cn, dt: (0.5*cv + 0.5*cn) >= 0.65)
eval_detector("CP-IDS Conjunctive (AND, 30s)",     lambda cv, cn, dt: (cv >= 0.5) and (cn >= 0.5) and (dt <= 30.0))
eval_detector("CP-IDS Tiered (AND-hi | Sng>=0.75)", lambda cv, cn, dt: ((cv >= 0.65) and (cn >= 0.65) and (dt <= 30.0)) or (cv >= 0.75) or (cn >= 0.75))

print("\n=== ANÁLISE DE SENSIBILIDADE DE JANELA DELTA_T (CP-IDS AND) ===")
for w in [5, 10, 30, 60]:
    eval_detector(f"Window dt <= {w}s", lambda cv, cn, dt, w=w: (cv >= 0.5) and (cn >= 0.5) and (dt <= w))
