import os; os.environ["OMP_NUM_THREADS"]="2"
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.tri as mtri
from matplotlib.patches import Ellipse, Rectangle, FancyArrowPatch
import pcf_fem as P
from pcf_fem import Design, make_mesh, fundamental
F="../results/figures/"; T,O,G,K="#0E7C86","#D95F02","#8A949B","#0F2F38"
plt.rcParams.update({"font.size":12})
# mesh + quarter model
d=Design(); m,tags=make_mesh(d); X,Y=d.window()
fig,ax=plt.subplots(1,2,figsize=(12,5.6))
tri=mtri.Triangulation(m.doflocs[0],m.doflocs[1],m.t.T); cm=np.array([0,0,1,2,3])[tags]
from matplotlib.colors import ListedColormap
for A in ax: A.tripcolor(tri,facecolors=cm.astype(float),cmap=ListedColormap(["#DCE6EC","#FFFFFF","#2A78B8","#F3D9B8"]),edgecolors="#7a8890",lw=.25,vmin=0,vmax=3); A.set_aspect("equal"); A.set_xlabel("x (µm)")
ax[0].set(title="Quarter model: 3472 triangles",ylabel="y (µm)"); ax[0].text(9.0,4,"PML",fontsize=14); ax[0].text(3,9.2,"PML",fontsize=14)
ax[0].text(.25,5.55,"x = 0 wall: PEC for x-pol",rotation=90,fontsize=10,color="#B00020",va="center",bbox=dict(fc="w",ec="none",alpha=.75,pad=1)); ax[0].text(5.2,.15,"y = 0 wall: PMC for x-pol",fontsize=10,color="#B00020",ha="center",bbox=dict(fc="w",ec="none",alpha=.75,pad=1))
ax[1].set(xlim=(0,2.6),ylim=(0,2.6),title="Zoom: core and liquid holes"); fig.tight_layout(); fig.savefig(F+"study_mesh.png",dpi=160); plt.close(fig)
# parameters annotated
fig,ax=plt.subplots(figsize=(6.4,5.8)); ax.set_facecolor("#DCE6EC")
for x,y,a,b,t in d.holes(): ax.add_patch(Ellipse((x,y),2*a,2*b,fc="w" if t==2 else "#2A78B8",ec=K))
def arr(a,b,t,xy,c=O): ax.add_patch(FancyArrowPatch(a,b,arrowstyle="<->",mutation_scale=12,color=c,lw=2)); ax.text(*xy,t,color=c,fontsize=12,fontweight="bold")
arr((2.4,0),(4.8,0),"Λ = 2.4 µm",(2.6,-.85)); arr((3.6,2.08),(3.6,3.08),"d$_a$=1",(3.72,2.45)); arr((3.6,2.08),(4.3,2.08),"d$_b$=0.7",(3.62,1.45)); arr((0,0),(0,1),"Λ$_{core}$=1",(.08,1.55),"#B00020")
ax.set(xlim=(-3.2,5.6),ylim=(-3.2,4.8),aspect="equal",xlabel="x (µm)",ylabel="y (µm)",title="V-PCF: dimensions are semi-axes"); fig.tight_layout(); fig.savefig(F+"study_dims.png",dpi=170); plt.close(fig)
# single field
q=fundamental(d,1.0,1.33,"x",guess=1.405,nev=6); e,ez=q.basis.interpolate(q.x); Z=q.basis.global_coordinates().value
E=np.sqrt(abs(e[0])**2+abs(e[1])**2).ravel(); x,y=Z[0].ravel(),Z[1].ravel(); s=(x<4.5)&(y<4.5); x,y,E=x[s],y[s],E[s]/E[s].max()
fig,A=plt.subplots(figsize=(6,5.2)); c=A.tricontourf(mtri.Triangulation(np.r_[x,-x,x,-x],np.r_[y,y,-y,-y]),np.r_[E,E,E,E],levels=np.linspace(0,1,26),cmap="viridis")
for hx,hy,a,b,t in d.holes(): A.add_patch(Ellipse((hx,hy),2*a,2*b,fc="none",ec="w",lw=1))
A.set(xlim=(-4,4),ylim=(-4,4),aspect="equal",xlabel="x (µm)",ylabel="y (µm)"); fig.colorbar(c,label="|E$_t$| (normalised)"); fig.tight_layout(); fig.savefig(F+"field_V.png",dpi=170); plt.close(fig)
# mode crossing
z=pd.read_csv("../results/diag_scan_V133.csv"); a=z[z["rank"]==0]
fig,ax=plt.subplots(1,2,figsize=(11,4.3)); ax[0].plot(a.lam,a.r,"o-",color=T,ms=4); ax[0].axvspan(.795,.805,color=O,alpha=.3); ax[0].plot([.8],[15.62],"s",color=O,ms=9,label="paper, 15.62 %"); ax[0].set(xlabel="Wavelength (µm)",ylabel="r (%)",title="Sensitivity of most core-like mode"); ax[0].legend()
ax[1].plot(a.lam,100*a.core,"o-",color=T,ms=4); ax[1].axhline(85,color=G,ls="--"); ax[1].text(.86,80,"85 % cutoff"); ax[1].set(xlabel="Wavelength (µm)",ylabel="Power in core region (%)",title="Dip = mixed with a cladding mode")
for A in ax: A.grid(alpha=.25)
fig.tight_layout(); fig.savefig(F+"study_crossing.png",dpi=160); plt.close(fig)
# roundoff
import ast
r=pd.read_csv("../results/diag_roundoff.csv"); fig,A=plt.subplots(figsize=(8.5,4.4)); pap={("H",1.33):2.4e-9,("H",1.366):7.2e-10,("V",1.33):2.2e-10,("V",1.354):4.9e-11,("V",1.366):3.7e-12}
for i,t in r.iterrows():
    A.plot([i]*3,[max(float(v),3e-13) for v in ast.literal_eval(t.eigenvalue)],"x",color=O,ms=9,label="direct eigenvalue, 3 tries" if i==0 else None); A.plot([i],[float(ast.literal_eval(t.identity)[0])],"o",color=T,ms=9,label="energy identity (stable)" if i==0 else None)
    if (t.kind,t.n) in pap: A.plot([i+.15],[pap[t.kind,t.n]],"s",color=K,ms=8,label="paper" if i==0 else None)
A.set_yscale("log"); A.set_xticks(range(6)); A.set_xticklabels([f"{t.kind}, {t.n}" for _,t in r.iterrows()]); A.set(ylabel="Loss at η = 1 (dB/m)"); A.grid(alpha=.25); A.legend(); A.text(.0,3.2e-13,"two values of exactly 0 are drawn at the bottom",fontsize=9); fig.tight_layout(); fig.savefig(F+"study_roundoff.png",dpi=160); plt.close(fig)
