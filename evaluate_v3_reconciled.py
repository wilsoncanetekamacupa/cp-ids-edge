import random, math

random.seed(42)
dataset = []
for _ in range(100): dataset.append(("G1", False, random.uniform(0.0, 0.25), random.uniform(0.0, 0.20), 999.0))
for i in range(100):
    if i < 50: dataset.append(("G2", False, random.uniform(0.65, 0.85), random.uniform(0.0, 0.20), 999.0))
    else:      dataset.append(("G2", False, random.uniform(0.0, 0.20), random.uniform(0.65, 0.85), 999.0))
for _ in range(100):
    dt = random.uniform(0.5, 22.0)
    cv = random.uniform(0.75, 0.98) if random.random() > 0.04 else random.uniform(0.30, 0.48)
    cn = random.uniform(0.75, 0.99)
    dataset.append(("G3", True, cv, cn, dt))
for _ in range(100):
    dt = random.uniform(1.0, 28.0)
    dataset.append(("G4", False, random.uniform(0.51, 0.68), random.uniform(0.51, 0.66), dt))
for i in range(100):
    if i < 50: dataset.append(("G5", True, random.uniform(0.78, 0.97), random.uniform(0.0, 0.20), 999.0))
    else:      dataset.append(("G5", True, random.uniform(0.0, 0.20), random.uniform(0.78, 0.98), 999.0))

test_set = []
for g_idx in range(5):
    test_set.extend(dataset[g_idx*100 + 50 : (g_idx+1)*100])

# 1. Teste Pareado de McNemar (Tier 1+2 vs Unimodal Cascade Ablation) no Test Set (N=250)
b = c = 0  # b: Tier1+2 acerta e Cascata erra; c: Cascata acerta e Tier1+2 erra
for _, is_att, cv, cn, dt in test_set:
    p_tiered  = (((cv >= 0.65) and (cn >= 0.65) and (dt <= 30.0)) or (cv >= 0.80) or (cn >= 0.80)) == is_att
    p_cascade = ((cv >= 0.80) or (cn >= 0.80)) == is_att
    if p_tiered and not p_cascade: b += 1
    elif not p_tiered and p_cascade: c += 1

# p-value exato binomial bicaudal para McNemar
n_disc = b + c
k_min = min(b, c)
p_val = sum(math.comb(n_disc, i) * (0.5 ** n_disc) for i in range(k_min + 1)) * 2.0
p_val = min(1.0, p_val)
print(f"McNemar (Tier 1+2 vs Cascade): concordantes={250-n_disc}, b(T1+2 ganha)={b}, c(Cascata ganha)={c}, p-value exato={p_val:.4f}")

# 2. Sensibilidade de Delta_t no Test Set (N=250)
for w in [5, 10, 30, 60]:
    TP = FP = TN = FN = 0
    for _, is_att, cv, cn, dt in test_set:
        pred = (cv >= 0.50) and (cn >= 0.50) and (dt <= w)
        if is_att and pred: TP += 1
        elif not is_att and pred: FP += 1
        elif not is_att and not pred: TN += 1
        elif is_att and not pred: FN += 1
    f1 = 2*TP / (2*TP + FP + FN) * 100
    print(f"Test Set AND dt <= {w:2d}s -> TP={TP}, FP={FP}, F1={f1:.1f}%")
