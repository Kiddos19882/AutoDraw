#!/usr/bin/env python3
"""V31: actual archived Egret BoardPane brush vs ideal geometric capsule, E3 not game E4."""
import argparse,base64,hashlib,json,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image
from io import BytesIO
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"/"preparation"))
from brush_footprint_geometry import swept_capsule_pixel_masks,footprint_pixel_bounds

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
WIDTHS=(1,3,10,20,30)
PATHS={
  "dot":[[230,120],[230,120]],
  "horizontal":[[215,120],[245,120]],
  "diagonal":[[215,105],[245,135]],
  "elbow":[[215,110],[230,110],[230,135]],
  "curved":[[210,125],[220,115],[230,112],[240,118],[250,127]],
  "roi_edge":[[155,100],[170,100]],
}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def frozen_fixtures():
    return [{"id":kind+"-w"+str(w),"kind":kind,"lineWidth":w,"points":points}
            for kind,points in PATHS.items() for w in WIDTHS]

def compare_case(fixture,case):
    if (case["id"]!=fixture["id"] or case["kind"]!=fixture["kind"] or
        case["lineWidth"]!=fixture["lineWidth"] or case["points"]!=fixture["points"]):
        raise ValueError("V31 native fixture identity mismatch")
    for threshold in (1,128):
        pixels=case["logicalAlpha"+str(threshold)]
        if len(pixels)>12000 or any(len(p)!=2 or type(p[0]) is not int or
          type(p[1]) is not int or p[0]<0 or p[0]>=460 or p[1]<0 or p[1]>=240 for p in pixels):
            raise ValueError("V31 malformed native logical pixel evidence")
        if len({tuple(p) for p in pixels})!=len(pixels):
            raise ValueError("V31 native logical points not unique")
    if not set(map(tuple,case["logicalAlpha128"])).issubset(
        set(map(tuple,case["logicalAlpha1"]))):
        raise ValueError("V31 native alpha threshold order mismatch")
    if case["backingAlpha1"]<case["backingAlpha128"]:
        raise ValueError("V31 alpha population invalid")
    capsule=swept_capsule_pixel_masks(fixture["points"],fixture["lineWidth"],1.0,1.0,460,240)
    potential=set(capsule["potential_cells"])
    guaranteed=set(capsule["guaranteed_cells"])
    if not guaranteed.issubset(potential):
        raise ValueError("Ideal capsule guarantee outside potential mask")
    # Native Egret alpha, not model coverage. Record both thresholds without tuning.
    alpha1=set(map(tuple,case["logicalAlpha1"]))
    alpha128=set(map(tuple,case["logicalAlpha128"]))
    roi=lambda pts:sum(not (155<=x<305 and 0<=y<240) for x,y in pts)
    return {
      "id":fixture["id"],"kind":fixture["kind"],"lineWidth":fixture["lineWidth"],
      "points":fixture["points"],"nativeLogicalAlpha1":len(alpha1),
      "nativeLogicalAlpha128":len(alpha128),
      "nativeBackingAlpha1":case["backingAlpha1"],
      "nativeBackingAlpha128":case["backingAlpha128"],
      "nativeOutsideSourceROI1":roi(alpha1),"nativeOutsideSourceROI128":roi(alpha128),
      "idealCapsulePotentialLogical":len(potential),
      "idealCapsuleGuaranteedLogical":len(guaranteed),
      "nativeAlpha1OutsideIdealPotential":len(alpha1-potential),
      "nativeAlpha128OutsideIdealPotential":len(alpha128-potential),
      "idealGuaranteedMissingInNativeAlpha1":len(guaranteed-alpha1),
      "idealGuaranteedMissingInNativeAlpha128":len(guaranteed-alpha128),
      "canvas2dVsWebgl":case["canvas2dVsWebgl"],
      "boardRenderMode":case["boardRenderMode"],"nativeDrawCalls":case["drawCalls"],
      "nativeTextureParameters":case["nativeTextureParameters"]
    }

def capture(workspace,fixtures):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):
            super().__init__(*a,directory=str(workspace.resolve()),**kw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    runner=threading.Thread(target=server.serve_forever,daemon=True);runner.start()
    driver=None
    try:
        options=Options();options.add_argument("-headless")
        options.set_preference("webgl.disabled",False)
        options.set_preference("webgl.force-enabled",True)
        options.set_preference("webgl.enable-webgl2",True)
        driver=webdriver.Firefox(options=options)
        driver.set_script_timeout(600)
        driver.set_page_load_timeout(180)
        driver.get("http://127.0.0.1:"+str(server.server_port)+
                   "/AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope")
        WebDriverWait(driver,120).until(
            lambda d:d.execute_script("return document.body.dataset.twoIconStatus")=="ready")
        payload=driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderV31NativeGameBrush(arguments[0]);",
            fixtures)
        payload["browser"]={"name":driver.capabilities.get("browserName"),
                            "version":driver.capabilities.get("browserVersion")}
        return payload
    finally:
        if driver:driver.quit()
        server.shutdown();server.server_close();runner.join(timeout=5)

def run(workspace,source,output):
    if sha(source)!=SOURCE_SHA or source.stat().st_size!=97308:
        raise ValueError("Pinned source SHA/length mismatch")
    with Image.open(source) as img:
        if img.size!=(200,320):raise ValueError("Pinned source dimension mismatch")
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("V31 never overwrite evidence")
    fixtures=frozen_fixtures()
    data=capture(workspace,fixtures)
    if data.get("schema")!="ENGINE001_V31_ACTUAL_EGRET_BRUSH" or (
        data.get("rasterScale")!=3 or data.get("board")!={"width":460,"height":240} or
        len(data["cases"])!=30 or data["blank"]["backingAlpha1"]!=0 or
        not data["blank"]["canvas2dVsWebgl"]["equal"]):
        raise ValueError("V31 archived native renderer result/blank mismatch")
    values=[]
    for fixture,item in zip(fixtures,data["cases"]):
        if not isinstance(item.get("canvas2dVsWebgl",{}).get("equal"),bool):
            raise ValueError("V31 Canvas2D backend outcome missing")
        if item.get("boardRenderMode")!=3:
            raise ValueError("V31 live scene board render mode mismatch")
        values.append(compare_case(fixture,item))
    urls=data.pop("representativePngDataUrls")
    if set(urls)!={"dot-w1","diagonal-w20","elbow-w30","roi_edge-w30"}:
        raise ValueError("V31 representative PNG population mismatch")
    output.mkdir(parents=True,exist_ok=True)
    for key,uri in urls.items():
        if not uri.startswith("data:image/png;base64,"):
            raise ValueError("V31 invalid native PNG")
        binary=base64.b64decode(uri.partition(",")[2],validate=True)
        with Image.open(BytesIO(binary)) as image:
            if image.size!=(1380,720):raise ValueError("V31 native PNG dimensions")
        (output/(key+".png")).write_bytes(binary)
    (output/"raw-native-cases.json").write_text(
        json.dumps(data["cases"],ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (output/"ideal-versus-native-cases.json").write_text(
        json.dumps(values,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    stats={
      "cases":len(values),
      "casesWithNativeAlpha1":sum(v["nativeLogicalAlpha1"]>0 for v in values),
      "casesWithNativeAlpha128":sum(v["nativeLogicalAlpha128"]>0 for v in values),
      "casesNativeAlpha1OutsideIdealPotential":sum(v["nativeAlpha1OutsideIdealPotential"]>0 for v in values),
      "casesNativeAlpha128OutsideIdealPotential":sum(v["nativeAlpha128OutsideIdealPotential"]>0 for v in values),
      "casesIdealGuaranteedNotNativeAt128":sum(v["idealGuaranteedMissingInNativeAlpha128"]>0 for v in values),
      "canvas2dVsWebglDifferent":sum(not v["canvas2dVsWebgl"]["equal"] for v in values),
      "totalNativeOutsideROIAlpha128CasePixels":sum(v["nativeOutsideSourceROI128"] for v in values)
    }
    hashes={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    report={
      "experiment":"ENGINE001_NATIVE_GAME_BRUSH_V31",
      "status":"ARCHIVED_EGRET_NATIVE_DIAGNOSTIC_NOT_GAME_E4",
      "source_sha256":SOURCE_SHA,
      "engineBundleFiles":{
        "engine":"AutoDraw_Stage20/gameEngine/mergeEngine_df2e5bc5.js",
        "game":"AutoDraw_Stage20/gameEngine/main.min_653f95bc.js"},
      "engineBundleSha256":{
        "engine":sha(workspace/"AutoDraw_Stage20/gameEngine/mergeEngine_df2e5bc5.js"),
        "game":sha(workspace/"AutoDraw_Stage20/gameEngine/main.min_653f95bc.js")},
      "browser":data["browser"],"engineVersion":data["engineVersion"],
      "glInfo":data["glInfo"],"blank":data["blank"],
      "matrix":{"widths":list(WIDTHS),"trajectories":PATHS},
      "metrics":stats,"derivedSha256":hashes,
      "modelUse":"ideal_capsule MODEL_ONLY compared to actual Egret native RGBA",
      "productionModified":False,
      "notTested":["live E4","exact run-bound CHALK","production adaptive fill",
                   "real game per-color >=99% coverage","<=3 logical px game leakage","E5"]
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for f in ("workspace","source","output"):p.add_argument("--"+f,type=Path,required=True)
    a=p.parse_args()
    run(a.workspace,a.source,a.output)
