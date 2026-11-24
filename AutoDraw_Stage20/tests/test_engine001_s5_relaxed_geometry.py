"""A9 MODEL_ONLY geometry contracts; native quality checked separately."""
import unittest
import numpy as np
import engine001_s5_relaxed_geometry as s

def masks():
    support=np.zeros((73,73),bool)
    support[35:38,35:38]=True
    return support,support.copy()

class RelaxedTests(unittest.TestCase):
    def test_soft_and_free(self):
        support,core=masks()
        target=np.zeros((12,12),bool); target[4:7,5]=True
        self.assertFalse(s.candidate_mask(target,support,core,0).any())
        self.assertTrue(s.candidate_mask(target,support,core,None)[5,5])
        self.assertFalse(s.candidate_mask(target,support,core,.5)[5,5])
        self.assertTrue(s.candidate_mask(target,support,core,.8)[5,5])
    def test_diagonal_maximal(self):
        valid=np.eye(8,dtype=bool)
        runs=s.runs_for_direction(valid,valid.astype(float),(1,1),1)
        self.assertEqual(runs,[((0,0),(7,7))])
    def test_singleton_and_fractional(self):
        support,core=masks()
        want=np.full((15,15,3),255,np.uint8);want[7,7]=0
        proof={"measurements":{f"{d}:4":{"lateral_min_backing_px":3} for d in ("horizontal","vertical")}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        mask=np.zeros((15,15),bool);mask[7,7]=True
        self.assertEqual(s.runs_for_direction(mask,mask.astype(float),(1,0),1),[((7,7),(7,7))])
        self.assertEqual(s.tap_end((7,7),mask.shape),(8,7))
        want[4:10,4:10]=0
        paths,_=s.plan(want,{4:(support,core)},proof,stroke,None)
        self.assertTrue(paths);s.validate(paths)
        self.assertTrue(any(p["x"]%1 or p["y"]%1 for a in paths for p in a["points"]))
    def test_no_forbidden_width(self):
        with self.assertRaises(ValueError):
            s.validate([dict(width=3,points=[dict(x=1,y=1),dict(x=2,y=2)])])
    def test_a10_treatments_and_compatibility(self):
        self.assertEqual(tuple(k for k,_ in s.A10_TREATMENTS),("10","20","30"))
        self.assertEqual(tuple(k for k,_ in s.TREATMENTS),("10","20","30","50","free"))
        support,core=masks()
        want=np.full((21,21,3),255,np.uint8)
        want[4:17,4:17]=0
        proof={"measurements":{f"{d}:{w}":{"lateral_min_backing_px":3}
                for d in ("horizontal","vertical") for w in range(1,11)}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        atlas={w:(support,core) for w in range(1,11)}
        allpaths,_=s.plan(want,atlas,proof,stroke,.3,widths=range(1,11))
        self.assertTrue(allpaths)
        s.validate(allpaths,range(1,11))
        self.assertTrue(all(1<=p["width"]<=10 for p in allpaths))
        legacy,_=s.plan(want,atlas,proof,stroke,.3)
        self.assertTrue(legacy)
        s.validate(legacy)
        self.assertTrue(all(4<=p["width"]<=10 for p in legacy))
        with self.assertRaises(ValueError):
            s.validate([dict(width=11,points=[dict(x=1,y=1),dict(x=2,y=2)])],range(1,11))

    def test_all_widths_eligible_and_repair(self):
        support,core=masks()
        want=np.full((15,15,3),255,np.uint8)
        want[3:12,3:12]=0
        proof={"measurements":{f"{d}:{w}":{"lateral_min_backing_px":3}
                for d in ("horizontal","vertical") for w in range(1,11)}}
        atlas={w:(support,core) for w in range(1,11)}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        paths,_=s.plan(want,atlas,proof,stroke,.2,widths=range(1,11))
        self.assertTrue(paths)
        actual=np.full_like(want,255)
        corrections,_=s.plan(want,atlas,proof,stroke,.2,actual,repair=True,widths=range(1,11))
        s.validate(corrections,range(1,11))
        self.assertTrue(all(p["width"] in atlas for p in corrections))
        self.assertTrue(all(p["width"] in range(1,11) for p in paths+corrections))

    def test_a11_mixed_limits_and_strict_taps(self):
        self.assertEqual(s.A11_TREATMENTS,(("10",.1),("20",.2)))
        for _,limit in s.A11_TREATMENTS:
            for w in range(1,11):
                self.assertEqual(s.width_tolerance(w,limit,True),0 if w<=3 else limit)
                self.assertEqual(s.width_tolerance(w,limit),limit)
        valid=np.zeros((5,5),bool);valid[2,2]=True
        runs=[((2,2),(2,2))]
        self.assertEqual(s.strict_taps(runs,valid),[])
        valid[2,1]=True
        self.assertEqual(s.strict_taps(runs,valid),[((2,2),(1,2))])

    def test_a12_distance_partition(self):
        want=np.full((30,30,3),255,np.uint8)
        want[2:28,2:28]=[70,80,90]
        want[12:18,12:18]=[20,40,60]
        maps=s.a12_distance_masks(want,5,1/3)
        self.assertEqual(set(maps),{0x46505a,0x14283c})
        for band,inside,distance in maps.values():
            self.assertFalse(np.any(band&inside))
            self.assertTrue(np.all(distance[band]>0))
        for color,(band,inside,_) in maps.items():
            target=np.all(want==np.array([(color>>16)&255,(color>>8)&255,color&255]),axis=2)
            self.assertTrue(np.array_equal(band|inside,target))
        counts=[int(sum(b.sum() for b,_,_ in s.a12_distance_masks(want,r,1/3).values())) for r in s.A12_RADII]
        self.assertEqual(counts,sorted(counts))
        self.assertEqual(s.A12_RADII,(3,5,10,15,20))

    def test_a12_runner_does_not_shadow_lane_phase_module(self):
        import ast
        from pathlib import Path
        src=Path(__file__).with_name("run_engine001_s5_native_adaptive_a6_z2.py").read_text("utf8")
        fn=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=="main")
        bindings=[]
        for n in ast.walk(fn):
            if isinstance(n,(ast.For,ast.AsyncFor)):
                bindings.extend(v.id for v in ast.walk(n.target) if isinstance(v,ast.Name))
        self.assertNotIn("phase",bindings)
        self.assertIn("phase.broad_plan",src)

    def test_a12_singleton_guard_applies_to_both_phases(self):
        # A12 must not rely on the historical tap_end() fallback because
        # the second endpoint could be outside its assigned region.
        core=np.zeros((73,73),bool);core[36,36]=True
        valid=np.zeros((7,7),bool);valid[3,3]=True
        benefit=valid.astype(np.float32)
        delta=valid.astype(np.int32)
        self.assertIsNone(s.choose(valid,benefit,delta,core,1,strict=True))
        self.assertIsNotNone(s.choose(valid,benefit,delta,core,1,strict=False))
        valid[3,4]=True
        chosen=s.choose(valid,valid.astype(np.float32),
                        valid.astype(np.int32),core,1,strict=True)
        self.assertIsNotNone(chosen)
        self.assertTrue(all(u != v for u,v in chosen[0]))
        self.assertTrue(all(valid[y,x] for u,v in chosen[0]
                            for x,y in (u,v)))

    def test_a12_phase_allocation(self):
        support=np.zeros((73,73),bool);support[36,36]=True
        want=np.full((26,26,3),255,np.uint8)
        want[1:25,1:25]=0
        atlas={w:(support, support.copy()) for w in range(1,11)}
        proof={"measurements":{f"{d}:{w}":{"lateral_min_backing_px":3}
                for d in ("horizontal","vertical") for w in range(1,11)}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        for radius in s.A12_RADII:
            for _,spill in s.A12_BROAD:
                paths,ledger,phases,regions=s.a12_plan(want,atlas,proof,stroke,spill,radius,1/3)
                s.validate(paths,range(1,11))
                self.assertEqual(len(paths),len(phases["boundary"])+len(phases["interior"]))
                self.assertTrue(all(p["width"]<=3 for p in phases["boundary"]))
                self.assertTrue(all(p["width"]>=4 for p in phases["interior"]))
                self.assertTrue(all(x["spill_proxy_limit"]==0 for x in ledger if x["phase"]=="boundary"))
                self.assertTrue(all(x["spill_proxy_limit"]==spill for x in ledger if x["phase"]=="interior"))
        with self.assertRaises(ValueError):
            s.a12_distance_masks(want,7,1)
        with self.assertRaises(ValueError):
            s.a12_plan(want,atlas,proof,stroke,.3,3,1/3)

    def test_white_repair(self):
        support,core=masks()
        want=np.full((15,15,3),255,np.uint8)
        actual=want.copy();actual[3:12,3:12]=0
        proof={"measurements":{f"{d}:4":{"lateral_min_backing_px":3} for d in ("horizontal","vertical")}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        paths,_=s.plan(want,{4:(support,core)},proof,stroke,None,actual,True)
        self.assertTrue(paths);self.assertTrue(all(p["colorRgb"]==0xffffff for p in paths));s.validate(paths)

if __name__=="__main__":
    unittest.main()
