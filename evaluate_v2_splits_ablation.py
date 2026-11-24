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
    if x < (a + 1.0) / (a + b + 2.0): return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b

def _beta_ppf(p, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _betainc(a, b, mid) < p: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

def cp_ci(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else _beta_ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return lo * 100.0, hi * 100.0

random.seed(42)
# Gera 500 trials (100 por grupo G1..G5)
# Pontuação de confiança: s_vis = max(conf_yolo, norm_laplacian), s_net = min(1.0, rate_norm)
dataset = []
for _ in range(100): dataset.append(("G1_Normal", False, random.uniform(0.0, 0.25), random.uniform(0.0, 0.20), 999.0))
for i in range(100):
    if i < 50: dataset.append(("G2_SingleNoise", False, random.uniform(0.65, 0.85), random.uniform(0.0, 0.20), 999.0))
    else:      dataset.append(("G2_SingleNoise", False, random.uniform(0.0, 0.20), random.uniform(0.65, 0.85), 999.0))
for _ in range(100):
    dt = random.uniform(0.5, 22.0)
    cv = random.uniform(0.75, 0.98) if random.random() > 0.04 else random.uniform(0.30, 0.48)
    cn = random.uniform(0.75, 0.99)
    dataset.append(("G3_HybridAttack", True, cv, cn, dt))
for _ in range(100):
    dt = random.uniform(1.0, 28.0)
    dataset.append(("G4_CoincidentBenign", False, random.uniform(0.51, 0.68), random.uniform(0.51, 0.66), dt))
for i in range(100):
    if i < 50: dataset.append(("G5_SingleAttack", True, random.uniform(0.78, 0.97), random.uniform(0.0, 0.20), 999.0))
    else:      dataset.append(("G5_SingleAttack", True, random.uniform(0.0, 0.20), random.uniform(0.78, 0.98), 999.0))

# Divisão estratificada 50/50: Treino (250) para calibrar limiares, Teste (250) para reportar métricas
train_set, test_set = [], []
for g_idx in range(5):
    grp = dataset[g_idx*100 : (g_idx+1)*100]
    train_set.extend(grp[:50])
    test_set.extend(grp[50:])

# Calibração no conjunto de treino (250 trials): encontra limiar ótimo de Tier 1 e Tier 2
best_f1, th_t1, th_t2 = -1, 0.65, 0.75
for t1 in [0.60, 0.65, 0.70]:
    for t2 in [0.72, 0.75, 0.80]:
        TP = FP = TN = FN = 0
        for _, is_att, cv, cn, dt in train_set:
            pred = ((cv >= t1) and (cn >= t1) and (dt <= 30.0)) or (cv >= t2) or (cn >= t2)
            if is_att and pred: TP += 1
            elif not is_att and pred: FP += 1
            elif not is_att and not pred: TN += 1
            elif is_att and not pred: FN += 1
        f1 = 2*TP / (2*TP + FP + FN) if (2*TP + FP + FN) else 0
        if f1 > best_f1: best_f1, th_t1, th_t2 = f1, t1, t2

print(f"=== CALIBRAÇÃO NO TREINO (N=250): th_Tier1={th_t1:.2f}, th_Tier2={th_t2:.2f} (F1 treino={best_f1*100:.1f}%) ===\n")

def evaluate_on(data, name, fn):
    TP = FP = TN = FN = 0
    by_grp = {g: [0, 0] for g in ["G1_Normal", "G2_SingleNoise", "G3_HybridAttack", "G4_CoincidentBenign", "G5_SingleAttack"]}
    for g, is_att, cv, cn, dt in data:
        p = fn(cv, cn, dt)
        by_grp[g][1] += 1
        if p: by_grp[g][0] += 1
        if is_att and p: TP += 1
        elif not is_att and p: FP += 1
        elif not is_att and not p: TN += 1
        elif is_att and not p: FN += 1
    prec = TP/(TP+FP)*100 if (TP+FP) else 0
    rec  = TP/(TP+FN)*100 if (TP+FN) else 0
    f1   = 2*prec*rec/(prec+rec) if (prec+rec) else 0
    fpr  = FP/(FP+TN)*100 if (FP+TN) else 0
    r_lo, r_hi = cp_ci(TP, TP+FN)
    f_lo, f_hi = cp_ci(FP, FP+TN)
    grp_str = " ".join([f"{k.split('_')[0]}:{v[0]}/{v[1]}" for k, v in by_grp.items()])
    print(f"{name:34s} | Prec:{prec:5.1f}% | Rec:{rec:5.1f}% [{r_lo:4.1f}-{r_hi:4.1f}] | F1:{f1:5.1f}% | FPR:{fpr:5.1f}% [{f_lo:4.1f}-{f_hi:4.1f}] | Disparos: {grp_str}")

print("=== AVALIAÇÃO NO CONJUNTO DE TESTE INDEPENDENTE (N=250) ===")
evaluate_on(test_set, "1. Vision Only (th>=0.50)",          lambda cv, cn, dt: cv >= 0.50)
evaluate_on(test_set, "2. Network Only (th>=0.50)",         lambda cv, cn, dt: cn >= 0.50)
evaluate_on(test_set, "3. OR Fusion (V>=0.5 or N>=0.5)",    lambda cv, cn, dt: (cv >= 0.50) or (cn >= 0.50))
evaluate_on(test_set, "4a. Weighted Sum (0.5V+0.5N>=0.55)", lambda cv, cn, dt: (0.5*cv + 0.5*cn) >= 0.55)
evaluate_on(test_set, "4b. Weighted Sum (0.5V+0.5N>=0.65)", lambda cv, cn, dt: (0.5*cv + 0.5*cn) >= 0.65)
evaluate_on(test_set, "5. Unimodal Cascade Ablation",       lambda cv, cn, dt: (cv >= th_t2) or (cn >= th_t2))
evaluate_on(test_set, "6. CP-IDS Conjunctive (AND>=0.50)",  lambda cv, cn, dt: (cv >= 0.50) and (cn >= 0.50) and (dt <= 30.0))
evaluate_on(test_set, "7a. CP-IDS Tier 1 ONLY (Containment)",lambda cv, cn, dt: (cv >= th_t1) and (cn >= th_t1) and (dt <= 30.0))
evaluate_on(test_set, "7b. CP-IDS Tier 1 + Tier 2 (Full)",  lambda cv, cn, dt: ((cv >= th_t1) and (cn >= th_t1) and (dt <= 30.0)) or (cv >= th_t2) or (cn >= th_t2))
