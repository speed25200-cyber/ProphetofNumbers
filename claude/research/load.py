import numpy as np, glob, os
D = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(D, "draws.npz")

def load():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return z["ids"], z["ts"], z["nums"], z["boost"], z["bonus"]
    rows = []
    for f in sorted(glob.glob(os.path.join(D, "..", "draws", "draws-*.csv"))):
        with open(f) as fh:
            fh.readline()
            for line in fh:
                p = line.strip().split(",")
                if len(p) < 24: continue
                rows.append([int(x) if x else -1 for x in p])
    a = np.array(rows, dtype=np.int64)
    a = a[np.argsort(a[:,0])]
    ids, ts, nums, boost, bonus = a[:,0], a[:,1], a[:,2:22].astype(np.int8), a[:,22], a[:,23]
    np.savez_compressed(CACHE, ids=ids, ts=ts, nums=nums, boost=boost, bonus=bonus)
    return ids, ts, nums, boost, bonus

def indicator(nums):
    N = nums.shape[0]
    M = np.zeros((N,80), dtype=np.uint8)
    M[np.repeat(np.arange(N),20), nums.reshape(-1)-1] = 1
    return M

if __name__ == "__main__":
    ids, ts, nums, boost, bonus = load()
    print("N =", len(ids), "| id range", ids[0], ids[-1], "| gaps:", int(np.sum(np.diff(ids)!=1)))
    print("ts step uniq:", np.unique(np.diff(ts), return_counts=True))
    print("sorted rows:", bool(np.all(np.diff(nums.astype(int),axis=1) > 0)))
    print("boost vals:", np.unique(boost, return_counts=True))
    print("bonus in set:", int(np.sum([bonus[i] in set(nums[i].tolist()) for i in range(2000)])), "/2000")
