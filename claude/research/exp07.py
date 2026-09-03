import numpy as np
from math import comb
from load import load, indicator
ids,ts,nums,boost,bonus=load(); N=len(ids); M=indicator(nums).astype(np.int8)

print("="*72); print("E22 lag-1 overlap HISTOGRAM vs exact hypergeometric")
ov=(M[:-1]&M[1:]).sum(1)
h=np.bincount(ov,minlength=21).astype(float)
e=np.array([comb(20,k)*comb(60,20-k)/comb(80,20)*(N-1) for k in range(21)])
m=e>5; chi=((h[m]-e[m])**2/e[m]).sum()
print("  chi2=%.2f df=%d z=%+.2f"%(chi,m.sum()-1,(chi-(m.sum()-1))/np.sqrt(2*(m.sum()-1))))
print("  k :", " ".join("%5d"%k for k in range(13)))
print("  z :", " ".join("%+5.1f"%((h[k]-e[k])/np.sqrt(e[k])) for k in range(13)))
vex=20*(20/80)*(60/80)*(60/79)
print("  Var(overlap)=%.5f  exact=%.5f  z=%+.2f"%(ov.var(),vex,(ov.var()-vex)/(np.sqrt(2)*vex/np.sqrt(N))))

print("="*72); print("E23 TRIPLE-draw overlap |A_t & A_t+1 & A_t+2|")
t3=(M[:-2]&M[1:-1]&M[2:]).sum(1)
h3=np.bincount(t3,minlength=21).astype(float)
pk=np.array([comb(20,k)*comb(60,20-k)/comb(80,20) for k in range(21)])
e3=np.zeros(21)
for k in range(21):
    for j in range(0,min(k,20)+1):
        e3[j]+=pk[k]*comb(k,j)*comb(80-k,20-j)/comb(80,20)
e3*=(N-2)
m=e3>5; chi=((h3[m]-e3[m])**2/e3[m]).sum()
print("  mean=%.5f exact=%.5f"%(t3.mean(),(e3*np.arange(21)).sum()/(N-2)))
print("  chi2=%.2f df=%d z=%+.2f"%(chi,m.sum()-1,(chi-(m.sum()-1))/np.sqrt(2*(m.sum()-1))))

print("="*72); print("E24 gap composition inside a draw (21 gaps summing to 60)")
nn=nums.astype(int)
g=np.concatenate([nn[:,:1]-1, np.diff(nn,axis=1)-1, 80-nn[:,-1:]],axis=1)
print("  check sum==60:",bool(np.all(g.sum(1)==60)))
gm=g.mean(0); ge=60/21
print("  mean gap per position vs %.4f : max dev %.4f (se %.4f)"%(ge,np.abs(gm-ge).max(),g.std()/np.sqrt(N)))
a=np.clip(g[:,:-1],0,7).reshape(-1); b=np.clip(g[:,1:],0,7).reshape(-1)
T=np.bincount(a*8+b,minlength=64).reshape(8,8).astype(float)
E=np.outer(T.sum(1),T.sum(0))/T.sum()
c=((T-E)**2/E).sum(); print("  consecutive-gap pair chi2=%.1f df=49 z=%+.2f"%(c,(c-49)/np.sqrt(98)))

print("="*72); print("E26 #odd / #low vs exact hypergeometric")
for nm,v in [("odd",(nn%2==1).sum(1)),("low<=40",(nn<=40).sum(1))]:
    h=np.bincount(v,minlength=21).astype(float)
    e=np.array([comb(40,k)*comb(40,20-k)/comb(80,20)*N for k in range(21)])
    m=e>5; c=((h[m]-e[m])**2/e[m]).sum()
    print("  %-8s chi2=%.2f df=%d z=%+.2f"%(nm,c,m.sum()-1,(c-(m.sum()-1))/np.sqrt(2*(m.sum()-1))))
s=nn.sum(1); sd_ex=np.sqrt(20*(60/79)*(80**2-1)/12)
print("  sum mean=%.3f (810.000)  sd=%.3f (exact %.3f)  z_mean=%+.2f"%(s.mean(),s.std(),sd_ex,(s.mean()-810)/(sd_ex/np.sqrt(N))))
