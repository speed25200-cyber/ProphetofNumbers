# Information conjointe I(bits pairs ; ensemble trie) par tirage, FY partiel par modulo.
# Pour un ensemble fixe, les 20! ordres sont equiprobables ; chaque ordre determine la suite j_k,
# donc les dix bits (j_k - k) mod 2, k pair. H(bits|ensemble) estime par Monte Carlo (Miller-Madow).
import random, math, sys
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 1)
NSETS=int(sys.argv[2]) if len(sys.argv)>2 else 24
NORD=int(sys.argv[3]) if len(sys.argv)>3 else 40000
def bits_of_order(order):
    a=list(range(1,81)); pos={v:i for i,v in enumerate(a)}
    b=0
    for k in range(20):
        v=order[k]; j=pos[v]                     # position actuelle de v (>= k)
        if k%2==0 and ((j-k)&1): b|=1<<(k//2)    # bit 0 de x_k = (j-k) mod 2 (modulus pair)
        # swap a[k], a[j]
        vk=a[k]; a[k],a[j]=a[j],vk; pos[a[k]]=k; pos[a[j]]=j
    return b
def bits_of_order_shuffle(order):
    # Collections.shuffle : for i=79..60 : j = x mod (i+1), swap a[i], a[j]; le tirage = a[79..60]
    a=list(range(1,81)); pos={v:i for i,v in enumerate(a)}
    b=0
    for i in range(79,59,-1):
        k=79-i; v=order[k]; j=pos[v]
        if k%2==0 and (j&1): b|=1<<(k//2)         # bit 0 de x = j mod 2 (modulus i+1 pair)
        vi=a[i]; a[i],a[j]=a[j],vi; pos[a[i]]=i; pos[a[j]]=j
    return b
def H_cond(fn):
    tot=0.0
    for s in range(NSETS):
        S=random.sample(range(1,81),20); cnt={}
        for _ in range(NORD):
            random.shuffle(S); b=fn(S); cnt[b]=cnt.get(b,0)+1
        H=-sum(c/NORD*math.log2(c/NORD) for c in cnt.values())
        H+=(len(cnt)-1)/(2*NORD*math.log(2))     # Miller-Madow
        tot+=H
    return tot/NSETS
for nom,fn in (("fy",bits_of_order),("shuffle",bits_of_order_shuffle)):
    H=H_cond(fn); print(nom, "H(bits|ens)=%.4f  I=%.4f bits/tirage  total=%d" % (H,10-H,round((10-H)*70560)))
