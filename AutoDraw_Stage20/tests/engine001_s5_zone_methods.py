"""Z2 fixed-game-palette method ablation; research only, never gameplay admission.

CN: learned color naming probabilities; CHROMA: original boundary chromaticity;
CCP: contour-guided adaptation; RTV: relative-TV IRLS structure estimate;
DE2000: actual CIEDE2000; GRAPH: weighted Potts alpha expansion; SPATIAL:
fixed-palette spatial quantization-inspired contextual ICM (not halftoning).
"""
from __future__ import annotations
import hashlib
import io
import math
import tarfile
import numpy as np
from scipy import ndimage, sparse, io as sio
from scipy.sparse.linalg import cg
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.feature import canny
from engine001_bpred_s4r1_rag3_hierarchy import _connected, _lab_means, _boundary_stats
from engine001_bpred_s4r1_dg1_source_detail_atoms import _protected_original_dots
import engine001_s5_zone_merge as z

BATCHES = {
    "local": ("cn", "chroma", "ccp", "de2000"),
    "global": ("rtv", "graph", "spatial"),
    "combined": ("cn-chroma-de2000", "cn-chroma-ccp-rtv-de2000", "all"),
}
FLAGS = {
    "cn": {"cn"}, "chroma": {"chroma"}, "ccp": {"ccp"}, "de2000": {"de2000"},
    "rtv": {"rtv"}, "graph": {"graph"}, "spatial": {"spatial"},
    "cn-chroma-de2000": {"cn","chroma","de2000"},
    "cn-chroma-ccp-rtv-de2000": {"cn","chroma","ccp","rtv","de2000"},
    "all": {"cn","chroma","ccp","rtv","de2000","spatial","graph"},
}
CN_URL = "https://thoth.inrialpes.fr/people/vandeweijer/code/ColorNaming.tar"
CN_MIRROR = "https://raw.githubusercontent.com/auto-Dog/color_name_enhancement/e75823f291da1fbae0fd58d4859b16747097303e/w2c.mat"
CN_NAMES = ["black","blue","brown","grey","green","orange","pink","purple","red","white","yellow"]


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def validate_table(table):
    table = np.asarray(table, np.float64)
    require(table.shape == (32768, 11) and np.isfinite(table).all()
            and (table >= 0).all() and np.allclose(table.sum(axis=1), 1, atol=.02),
            "invalid color naming probability table")
    return table / table.sum(axis=1, keepdims=True)


def load_cn():
    import requests
    errors = []
    for url in (CN_URL, CN_MIRROR):
        try:
            response = requests.get(url, timeout=(15,45))
            response.raise_for_status()
            raw = response.content
            require(len(raw) <= 32*1024*1024, "oversized CN input")
            if url == CN_URL:
                with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tar:
                    candidates = [m for m in tar.getmembers() if m.isfile()
                        and m.name.rsplit("/",1)[-1].lower() in ("w2c.mat","w2c.txt")]
                    require(bool(candidates), "CN table not in author archive")
                    member = sorted(candidates, key=lambda m: (not m.name.lower().endswith(".mat"),m.name))[0]
                    require(member.size <= 24*1024*1024,"oversized CN member")
                    table_raw = tar.extractfile(member).read()
                    name = member.name
            else:
                table_raw, name = raw, "w2c.mat"
            if name.lower().endswith(".mat"):
                mat = sio.loadmat(io.BytesIO(table_raw))
                table = mat["w2c"]
            else:
                table = np.loadtxt(io.BytesIO(table_raw))
                if table.shape == (32768,14):
                    table = table[:,3:]
            table = validate_table(table)
            # Check index ordering and basic color-name semantics.
            probes = np.array([[0,0,0],[255,255,255],[255,0,0],[0,0,255]],np.uint8)
            require(np.array_equal(cn_probabilities(probes,table).argmax(axis=1),[0,9,8,1]),
                    "CN channel/order probe failed")
            return table, dict(url=url, member=name, archive_sha256=hashlib.sha256(raw).hexdigest(),
                table_sha256=hashlib.sha256(table_raw).hexdigest(), names=CN_NAMES, prior_errors=errors)
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("CN model unavailable: " + "; ".join(errors))


def cn_probabilities(rgb, table):
    i = np.asarray(rgb,np.int32)//8
    return table[i[...,0]+32*i[...,1]+1024*i[...,2]]


def palette_compatibility(palette, cn=None):
    lab = rgb2lab(palette.reshape(1,-1,3)).reshape(-1,3)
    chroma = np.linalg.norm(lab[:,1:],axis=1)
    neutral = (np.ptp(palette.astype(np.int16),axis=1)==0)|(chroma<=5)
    hue = np.degrees(np.arctan2(lab[:,2],lab[:,1]))
    diff = np.abs((hue[:,None]-hue[None,:]+180)%360-180)
    lum = np.abs(lab[:,0,None]-lab[None,:,0])
    compatible = (neutral[:,None]==neutral[None,:]) & np.where(neutral[:,None],lum<=30,diff<=45)
    if cn is not None:
        probs = cn_probabilities(palette,cn)
        overlap = np.minimum(probs[:,None,:],probs[None,:,:]).sum(axis=2)
        compatible &= overlap>=.25
    white = np.all(palette==255,axis=1)
    compatible &= white[:,None]==white[None,:]
    np.fill_diagonal(compatible,True)
    return compatible, neutral, lab


def masked_gaussian(x, mask, sigma):
    den=ndimage.gaussian_filter(mask.astype(float),sigma,mode="nearest")
    if x.ndim==3:
        return np.stack([masked_gaussian(x[...,k],mask,sigma) for k in range(x.shape[2])],axis=2)
    num=ndimage.gaussian_filter(np.where(mask,x,0.),sigma,mode="nearest")
    return np.where(mask,num/np.maximum(den,1e-12),x)


def pixel_edges(mask):
    idx=np.full(mask.shape,-1,np.int32)
    idx[mask]=np.arange(mask.sum())
    h=mask[:,:-1]&mask[:,1:]
    v=mask[:-1]&mask[1:]
    return idx,h,v,np.concatenate([idx[:,:-1][h],idx[:-1][v]]),np.concatenate([idx[:,1:][h],idx[1:][v]])


def rtv(lab, mask):
    """Directional relative-TV IRLS: coherent gradients get lower regularization."""
    if not mask.any():
        return lab.copy()
    idx,h,v,u,w=pixel_edges(mask)
    n=int(mask.sum())
    src=lab/100.
    out=src.copy()
    for _ in range(4):
        gx=np.zeros_like(out);gy=np.zeros_like(out)
        gx[:,:-1]=np.where(h[...,None],out[:,1:]-out[:,:-1],0)
        gy[:-1]=np.where(v[...,None],out[1:]-out[:-1],0)
        weights=[]
        for g,m,sl in ((gx,h,(slice(None),slice(None,-1))),(gy,v,(slice(None,-1),slice(None)))):
            absgrad=np.linalg.norm(g,axis=2)
            inherent=np.linalg.norm(masked_gaussian(g,mask,3.),axis=2)
            # IRLS approximation to windowed TV / windowed inherent variation.
            weight=masked_gaussian(1/(inherent+.01),mask,3.)/(absgrad+.01)
            weights.append(weight[sl][m])
        c=.015*np.concatenate(weights)
        diag=1+np.bincount(u,weights=c,minlength=n)+np.bincount(w,weights=c,minlength=n)
        M=sparse.csr_matrix((np.r_[diag,-c,-c],(np.r_[np.arange(n),u,w],np.r_[np.arange(n),w,u])),shape=(n,n))
        pre=sparse.diags(1/diag)
        for channel in range(3):
            x,info=cg(M,src[...,channel][mask],x0=out[...,channel][mask],M=pre,rtol=1e-6,atol=0,maxiter=500)
            require(info==0 and np.isfinite(x).all(),"RTV solver did not converge")
            out[...,channel][mask]=x
    return out*100.


def contour_map(lab, mask):
    # Long, coherent original luminance OR chromatic contours, not palette edges.
    edges=np.zeros(mask.shape,bool)
    for k in range(3):
        scale=100. if k==0 else 128.
        edges |= canny(lab[...,k]/scale,sigma=1.,low_threshold=.035,high_threshold=.10,mask=mask)
    ids,n=ndimage.label(edges,structure=np.ones((3,3),np.uint8))
    counts=np.bincount(ids.ravel(),minlength=n+1)
    keep=counts>=8
    keep[0]=False
    return ndimage.binary_dilation(keep[ids],iterations=1)&mask


def region_cost(ids, features, palette_lab, metric=False):
    n=int(ids.max())
    x=features[ids>0]
    owner=ids[ids>0]
    counts=np.bincount(owner,minlength=n+1)
    costs=np.zeros((n+1,len(palette_lab)),float)
    for i,c in enumerate(palette_lab):
        d=deltaE_ciede2000(x,np.broadcast_to(c,x.shape)) if metric else np.linalg.norm(x-c,axis=1)
        costs[:,i]=np.bincount(owner,weights=d*d,minlength=n+1)
    return costs,counts


def edge_data(ids, lab, contour):
    pair,length,mean,strong=_boundary_stats(ids,lab)
    chroma_pair,_,abmean,_=_boundary_stats(ids,np.concatenate([np.zeros((*ids.shape,1)),lab[...,1:]],axis=2))
    require(np.array_equal(pair,chroma_pair),"boundary pair drift")
    n=int(ids.max())+1
    keylist=[]; hits=[]
    for a,b,ca,cb in ((ids[:,:-1],ids[:,1:],contour[:,:-1],contour[:,1:]),
                      (ids[:-1],ids[1:],contour[:-1],contour[1:])):
        ok=(a>0)&(b>0)&(a!=b)
        keylist.append(np.minimum(a[ok],b[ok]).astype(np.int64)*n+np.maximum(a[ok],b[ok]))
        hits.append((ca[ok]|cb[ok]).astype(float))
    keys,inv=np.unique(np.concatenate(keylist),return_inverse=True)
    count=np.bincount(inv,weights=np.concatenate(hits),minlength=len(keys))
    require(np.array_equal(keys,pair[:,0].astype(np.int64)*n+pair[:,1]),"contour pair drift")
    return pair,length,mean,strong,abmean,count/np.maximum(length,1)


class Context:
    def __init__(self,original,target,flags,cn=None):
        self.original=original
        self.target=target
        self.flags=flags
        self.palette,self.base,self.fg,self.base_ids=z.zone_labels(target)
        self.compat,self.neutral,self.plab=palette_compatibility(self.palette,cn if "cn" in flags else None)
        self.lab=rgb2lab(original[...,:3])
        require(not np.any(self.fg&(original[...,3]!=255)),"foreground alpha mismatch")
        self.protected=_protected_original_dots(self.lab,original[...,3]==255)&self.fg
        self.contour=contour_map(self.lab,self.fg) if "ccp" in flags else np.zeros(self.fg.shape,bool)
        self.features=rtv(self.lab,self.fg) if "rtv" in flags else self.lab
        self.local=masked_gaussian(self.features,self.fg,1.5) if "spatial" in flags else self.features
        self.initial=np.square(self.lab-self.plab[self.base]).sum(axis=2)
        self.base_cn=cn if "cn" in flags else None

    def state(self,index,spatial=False,metric=False):
        ids=_connected(np.where(self.fg,index+1,0))
        n=int(ids.max())
        counts,_,means=_lab_means(ids,self.lab)
        _,_,feature_means=_lab_means(ids,self.features)
        owner=np.zeros(n+1,np.int32);owner[ids[self.fg]]=index[self.fg]
        orig,_=region_cost(ids,self.lab,self.plab)
        costs,_=region_cost(ids,self.features,self.plab,metric=metric)
        if spatial:
            local_cost,_=region_cost(ids,self.local,self.plab,metric=metric)
            costs=(costs+local_cost)*.5
        initial=np.bincount(ids[self.fg],weights=self.initial[self.fg],minlength=n+1)
        allowed=np.ones((n+1,len(self.palette)),bool)
        # Every constituent A5 pixel retains immutable allowed classes/hue.
        for k in range(len(self.palette)):
            invalid=self.fg & ~self.compat[self.base,k]
            allowed[:,k] &= np.bincount(ids[invalid],minlength=n+1)==0
        allowed &= (orig-initial[:,None])<=300*np.maximum(counts[:,None],1)+1e-8
        blocked=np.bincount(ids[self.protected],minlength=n+1)>0
        allowed[blocked]=False
        allowed[blocked,owner[blocked]]=True
        if "ccp" in self.flags:
            anchor_ids=ids[self.contour & self.fg]
            anchors=self.lab[self.contour & self.fg]
            base_anchor=np.square(anchors-self.plab[self.base[self.contour & self.fg]]).sum(axis=1)
            for k,c in enumerate(self.plab):
                inc=np.square(anchors-c).sum(axis=1)-base_anchor
                allowed[:,k] &= np.bincount(anchor_ids,weights=inc,minlength=n+1)<=1e-8
        # Existing assignment must always remain available; any newly proposed label is constrained.
        allowed[np.arange(n+1),owner]=True
        pair,length,mean,strong,abmean,coherent=edge_data(ids,self.lab,self.contour)
        return ids,owner,counts,means,feature_means,orig,costs,allowed,pair,length,mean,strong,abmean,coherent

    def verify(self,index):
        require(np.array_equal(self.fg,np.any(self.palette[index]!=255,axis=2)),"foreground changed")
        require(np.all(self.compat[self.base[self.fg],index[self.fg]]),"immutable color compatibility violated")
        require(np.array_equal(index[self.protected],self.base[self.protected]),"protected dot changed")


def local_merge(ctx,index):
    ledger=[]
    flags=ctx.flags
    while True:
        ids,owner,counts,means,fmeans,orig,cost,allowed,pair,length,mean,strong,abmean,coherent=ctx.state(index,metric="de2000" in flags)
        candidates=[]
        for j,(u,v) in enumerate(pair):
            u,v=int(u),int(v)
            if mean[j]>14 or strong[j]>.50 or not ctx.compat[owner[u],owner[v]]:
                continue
            if "de2000" in flags:
                if deltaE_ciede2000(fmeans[u],fmeans[v])>18 or deltaE_ciede2000(ctx.plab[owner[u]],ctx.plab[owner[v]])>25:
                    continue
            elif np.linalg.norm(fmeans[u]-fmeans[v])>24 or np.linalg.norm(ctx.plab[owner[u]]-ctx.plab[owner[v]])>60:
                continue
            if "chroma" in flags and (abmean[j]>9 or np.linalg.norm(means[u,1:]-means[v,1:])>14):
                continue
            if "ccp" in flags and coherent[j]>.5 and mean[j]>=8:
                continue
            for src,dst in ((u,v),(v,u)):
                if not allowed[src,owner[dst]]:
                    continue
                inc=float(cost[src,owner[dst]]-cost[src,owner[src]])
                candidates.append((inc,-int(length[j]),src,dst))
        if not candidates:
            break
        touched=set();remap=owner.copy();merges=[]
        for inc,ln,src,dst in sorted(candidates):
            if src in touched or dst in touched:
                continue
            touched.update((src,dst));remap[src]=owner[dst]
            merges.append(dict(source=src,destination=dst,pixels=int(counts[src]),cost_delta=inc,
                from_color=bytes(ctx.palette[owner[src]]).hex(),to_color=bytes(ctx.palette[owner[dst]]).hex()))
        index=np.where(ctx.fg,remap[ids],index)
        n=int(_connected(np.where(ctx.fg,index+1,0)).max())
        require(n<=len(owner)-1-len(merges),"non-decreasing local region count")
        ctx.verify(index)
        ledger.append(dict(before=len(owner)-1,after=n,merges=merges))
    return index,ledger


def energy(labels,unary,pair,weight):
    return float(unary[np.arange(len(labels)),labels].sum()+weight[labels[pair[:,0]]!=labels[pair[:,1]]].sum())


def expansion(labels,alpha,unary,allowed,pair,weight):
    import maxflow
    n=len(labels)
    stay=unary[np.arange(n),labels].copy()
    move=unary[:,alpha].copy()
    u,v=pair.T
    e00=weight*(labels[u]!=labels[v])
    e01=weight*(labels[u]!=alpha)
    e10=weight*(alpha!=labels[v])
    c=(e01+e10-e00)*.5
    require(np.all(c>=-1e-8),"non-submodular expansion")
    np.add.at(move,u,e10-e00-c)
    np.add.at(move,v,e01-e00-c)
    # Strictly prohibit incompatible assignments, with data-dependent finite bound.
    bound=1+np.abs(stay).sum()+np.abs(move).sum()+weight.sum()*4
    move[~allowed[:,alpha]]=bound
    low=np.minimum(stay,move)
    g=maxflow.Graph[float](n,len(pair))
    g.add_nodes(n)
    for i in range(n):
        g.add_tedge(i,float(move[i]-low[i]),float(stay[i]-low[i]))
    for i,j,w in zip(u,v,c):
        if w>0:
            g.add_edge(int(i),int(j),float(w),float(w))
    g.maxflow()
    proposal=labels.copy()
    for i in range(n):
        if g.get_segment(i)==1:
            proposal[i]=alpha
    require(np.all(allowed[np.arange(n),proposal]),"forbidden cut label")
    return proposal


def optimize(ctx,index,method):
    ids,owner,counts,means,fmeans,orig,cost,allowed,pair,length,mean,strong,abmean,coherent=ctx.state(index,spatial=method=="spatial",metric="de2000" in ctx.flags)
    labels=owner[1:].copy()
    unary=cost[1:]
    allowed=allowed[1:]
    pair=pair-1
    weight=(120 if method=="graph" else 90)*length*np.exp(-np.square(mean/15.))
    if "chroma" in ctx.flags:
        weight*=np.exp(-np.square(abmean/9.))
    if "ccp" in ctx.flags:
        weight*=1-np.where(mean>=8,coherent,0)
    trace=[energy(labels,unary,pair,weight)]
    adjacency=[[] for _ in labels]
    for (u,v),w in zip(pair,weight):
        adjacency[u].append((v,w));adjacency[v].append((u,w))
    for _ in range(6):
        prev=trace[-1]
        if method=="graph":
            for alpha in range(len(ctx.palette)):
                candidate=expansion(labels,alpha,unary,allowed,pair,weight)
                value=energy(candidate,unary,pair,weight)
                if value<trace[-1]-1e-7:
                    labels=candidate;trace.append(value)
        else:
            for i in range(len(labels)):
                costs=unary[i].copy()
                for j,w in adjacency[i]:
                    costs+=w*(np.arange(len(costs))!=labels[j])
                costs[~allowed[i]]=np.inf
                k=int(costs.argmin())
                if costs[k]<costs[labels[i]]-1e-7:
                    labels[i]=k
            value=energy(labels,unary,pair,weight)
            require(value<=trace[-1]+1e-6,"ICM energy regression")
            trace.append(value)
        if trace[-1]>=prev-1e-7:
            break
    remap=np.r_[0,labels]
    index=np.where(ctx.fg,remap[ids],index)
    ctx.verify(index)
    return index,dict(method=method,energy=trace,region_nodes=len(labels))


def run_variant(original,target,variant,cn=None):
    require(variant in FLAGS,"unknown variant")
    flags=FLAGS[variant]
    require("cn" not in flags or cn is not None,"CN table missing")
    ctx=Context(original,target,flags,cn)
    index=ctx.base.copy()
    ledger={}
    if flags-{"graph","spatial"}:
        index,ledger["local"]=local_merge(ctx,index)
    if "spatial" in flags:
        index,ledger["spatial"]=optimize(ctx,index,"spatial")
    if "graph" in flags:
        index,ledger["graph"]=optimize(ctx,index,"graph")
    ctx.verify(index)
    output=ctx.palette[index]
    before,before_ids=z.region_counts(target)
    after,after_ids=z.region_counts(output)
    transitions=np.zeros((len(ctx.palette),len(ctx.palette)),np.int64)
    np.add.at(transitions,(ctx.base[ctx.fg],index[ctx.fg]),1)
    report=dict(variant=variant,flags=sorted(flags),before=before,after=after,
        changed_pixels=int(np.any(output!=target,axis=2).sum()),
        protected_dots=int(ctx.protected.sum()),contour_pixels=int(ctx.contour.sum()),
        colors=[bytes(c).hex() for c in ctx.palette],transitions=transitions.tolist(),
        neutral_to_chromatic=int(transitions[ctx.neutral][:,~ctx.neutral].sum()),
        chromatic_to_neutral=int(transitions[~ctx.neutral][:,ctx.neutral].sum()),
        quality_before=z.quality(original,target),quality_after=z.quality(original,output))
    return output,before_ids,after_ids,ctx.protected,report,ledger
