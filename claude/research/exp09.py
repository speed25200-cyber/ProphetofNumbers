import numpy as np
from math import comb
from load import load, indicator
ids,ts,nums,boost,bonus=load(); N=len(ids); M=indicator(nums).astype(np.int8)
e=np.array([comb(20,k)*comb(60,20-k)/comb(80,20) for k in range(21)])

print("="*74)
print("E29  lag-1 overlap: split-half replication of the cell deviations")
ov=(M[:-1]&M[1:]).sum(1); H=len(ov)//2
def cellz(o):
    h=np.bincount(o,minlength=21).astype(float); ee=e*len(o)
    return (h-ee)/np.sqrt(ee), ee
zA,_=cellz(ov[:H]); zB,_=cellz(ov[H:]); zAll,eeAll=cellz(ov)
print("   k  :", " ".join("%6d"%k for k in range(1,13)))
print("   all:", " ".join("%+6.2f"%zAll[k] for k in range(1,13)))
print("   1st:", " ".join("%+6.2f"%zA[k] for k in range(1,13)))
print("   2nd:", " ".join("%+6.2f"%zB[k] for k in range(1,13)))
m=np.arange(1,13)
r=np.corrcoef(zA[m],zB[m])[0,1]
print("   corr(1st half z, 2nd half z) over cells 1..12 = %+.3f   (a real effect replicates: r>0)"%r)
same=int(np.sum(np.sign(zA[m])==np.sign(zB[m])))
print("   cells with the same sign in both halves: %d/12  (binomial p=%.3f)"
      %(same, 2*min(sum(comb(12,i) for i in range(same,13)),sum(comb(12,i) for i in range(0,same+1)))/2**12))
print("   -> the k=8 cell:  all %+.2f | 1st %+.2f | 2nd %+.2f"%(zAll[8],zA[8],zB[8]))

print("\nE30  same check on the 'repeat rate' itself, per number, split-half")
Mf=M.astype(float)
rep=(Mf[:-1]*Mf[1:])                       # number j in both t and t+1
cA=rep[:H].sum(0); nA=Mf[:H].sum(0)
cB=rep[H:].sum(0); nB=Mf[H:-1].sum(0)
pA=cA/nA; pB=cB/nB
print("   P(j repeats | j drawn), 1st half mean %.5f  2nd half mean %.5f  (null 0.25)"%(pA.mean(),pB.mean()))
zA2=(pA-0.25)/np.sqrt(0.25*0.75/nA); zB2=(pB-0.25)/np.sqrt(0.25*0.75/nB)
print("   corr of the 80 per-number z between halves = %+.3f  (null 0)"%np.corrcoef(zA2,zB2)[0,1])
print("   max|z| 1st %.2f  2nd %.2f  ; pooled sum z^2 = %.1f (E=80)"
      %(np.abs(zA2).max(),np.abs(zB2).max(),(((rep.sum(0)/Mf[:-1].sum(0))-0.25)/np.sqrt(0.25*0.75/Mf[:-1].sum(0))**1).__pow__(2).sum()))
