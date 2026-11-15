#!/usr/bin/env python3
"""V24 lossless native pixel provenance of archived Egret width1; diagnostic only."""
import argparse,base64,hashlib,json,threading
from io import BytesIO
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from run_engine001_anilines_v23 import check_input,digest

def source_roi(source):
    with Image.open(source) as image:
        arr=np.asarray(image.convert("RGB").resize((150,240),Image.Resampling.LANCZOS))
    if arr.shape!=(240,150,3):raise ValueError("V24 source ROI dimension")
    return arr

def classify_alpha(case,fixture,palette,roi):
    pixels=case["alphaCoordinates"]
    if len(pixels)>250 or not pixels:raise ValueError("Missing/bounded native alpha")
    center=fixture["points"][0]
    sx=int(center["x"])-155;sy=int(center["y"])
    if not (0<=sx<150 and 0<=sy<240):raise ValueError("Bad center source ROI")
    label=int(palette[sy][sx])
    rgb=roi[sy,sx].astype(np.int16)
    totals={str(t):{"alphaPixels":0,"foreignClassPixels":0,"outsideRoiPixels":0,
                    "distance_ge_16":0,"distance_ge_32":0,
                    "distance_ge_64":0,"distance_ge_96":0,
                    "same_class_far_rgb_ge_64":0,
                    "different_class_near_rgb_lt_32":0}
            for t in (1,64,128,254)}
    for x,y,alpha in pixels:
        if not (type(x) is int and type(y) is int and type(alpha) is int and
                0<=x<1380 and 0<=y<720 and 1<=alpha<=255):
            raise ValueError("V24 invalid native backing pixel")
        xx=x//3-155;yy=y//3
        outside=not(0<=xx<150 and 0<=yy<240)
        foreign=False;distance=0
        if not outside:
            foreign=int(palette[yy][xx])!=label
            distance=int(np.max(np.abs(roi[yy,xx].astype(np.int16)-rgb)))
        for threshold in (1,64,128,254):
            if alpha<threshold:continue
            q=totals[str(threshold)];q["alphaPixels"]+=1
            if outside:q["outsideRoiPixels"]+=1
            else:
                if foreign:q["foreignClassPixels"]+=1
                for t in (16,32,64,96):
                    if distance>=t:q["distance_ge_"+str(t)]+=1
                if not foreign and distance>=64:q["same_class_far_rgb_ge_64"]+=1
                if foreign and distance<32:q["different_class_near_rgb_lt_32"]+=1
    for t in totals:
        if any(totals[t][key]!=case["coverage"][t][key] for key in
               ("alphaPixels","foreignClassPixels","outsideRoiPixels")):
            raise ValueError("V24 lossless pixels do not reproduce frozen V23 "+case["id"])
    return {"id":case["id"],"kind":case["kind"],"centerPaletteClass":label,
            "centerRgb":rgb.tolist(),"counts":totals,
            "nativeDrawCalls":case["nativeDrawCalls"],
            "alphaCoordinates":pixels}

def browser_run(workspace,fixtures,palette):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(workspace),**kw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    driver=None
    try:
        options=Options();options.add_argument("-headless")
        options.set_preference("webgl.disabled",False)
        options.set_preference("webgl.force-enabled",True)
        options.set_preference("webgl.enable-webgl2",True)
        driver=webdriver.Firefox(options=options)
        driver.set_page_load_timeout(180);driver.set_script_timeout(600)
        driver.get(f"http://127.0.0.1:{server.server_port}/AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope")
        WebDriverWait(driver,120).until(lambda d:d.execute_script(
            "return document.body.dataset.twoIconStatus")=="ready")
        result=driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderV24NativeAlphaProvenance(arguments[0],arguments[1]);",
            fixtures,palette)
        if result.get("schema")!="ENGINE001_V24_NATIVE_ALPHA_PROVENANCE":
            raise ValueError("Wrong V24 response")
        result["browserCapabilities"]={"browser":driver.capabilities.get("browserName"),
                                        "version":driver.capabilities.get("browserVersion")}
        return result
    finally:
        if driver:driver.quit()
        server.shutdown();server.server_close();thread.join(timeout=5)

def run(workspace,v22,v23,source,ani,output):
    fixtures,palette,v22_report=check_input(v22,source,ani)
    frozen=json.loads((v23/"report.json").read_text(encoding="utf8"))
    original_cases=json.loads((v23/"cases.json").read_text(encoding="utf8"))
    if (frozen["source_sha256"]!=v22_report["source_sha256"] or
        frozen["anilines_sha256"]!=v22_report["anilines_sha256"] or
        frozen["baseline_supported_source_pixels"]!=5812 or
        len(original_cases)!=89 or
        not all(digest(v23/f)==h for f,h in frozen["artifacts_sha256"].items())):
        raise ValueError("Frozen V23 report/digest baseline mismatch")
    if output.exists() and any(output.iterdir()):
        raise ValueError("V24 evidence overwrite prohibited")
    observed=browser_run(workspace,fixtures,palette)
    native=observed["native"]
    if len(native["cases"])!=89 or observed["blank"]["nonTransparent"]!=0:
        raise ValueError("V24 negative blank control failed; no footprint acceptance")
    roi=source_roi(source)
    row=np.asarray(palette,dtype=np.uint8)
    result=[]
    for obs,prior,fixture in zip(native["cases"],original_cases,fixtures):
        if (obs["id"]!=prior["id"] or obs["id"]!=fixture["id"] or
            obs["coverage"]!=prior["coverage"] or
            obs["firstPaletteClass"]!=prior["firstPaletteClass"] or
            obs["canvas2dVsWebgl"]!=prior["canvas2dVsWebgl"]):
            raise ValueError("V24 native raster disagrees with original V23: "+str(fixture["id"]))
        if not obs["canvas2dVsWebgl"]["equal"]:
            raise ValueError("V24 native Canvas2D vs WebGL mismatch")
        result.append(classify_alpha(obs,fixture,row,roi))
    output.mkdir(parents=True,exist_ok=True)
    files={}
    raw=base64.b64decode(observed["blank"].pop("png").partition(",")[2],validate=True)
    blank=output/"blank-control.png";blank.write_bytes(raw)
    with Image.open(BytesIO(raw)) as image:
        if image.size!=(1380,720):raise ValueError("V24 blank PNG dimensions")
    files[blank.name]=digest(blank)
    data=output/"per-case-native-alpha.json"
    data.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    files[data.name]=digest(data)
    def aggregate(items):
        return {"cases":len(items),"alpha_pixels_128":sum(a["counts"]["128"]["alphaPixels"] for a in items),
                "foreign_palette_pixels_128":sum(a["counts"]["128"]["foreignClassPixels"] for a in items),
                "same_palette_far_rgb_64":sum(a["counts"]["128"]["same_class_far_rgb_ge_64"] for a in items),
                "other_palette_near_rgb_32":sum(a["counts"]["128"]["different_class_near_rgb_lt_32"] for a in items),
                "raw_rgb_ge_16":sum(a["counts"]["128"]["distance_ge_16"] for a in items),
                "raw_rgb_ge_32":sum(a["counts"]["128"]["distance_ge_32"] for a in items),
                "raw_rgb_ge_64":sum(a["counts"]["128"]["distance_ge_64"] for a in items),
                "raw_rgb_ge_96":sum(a["counts"]["128"]["distance_ge_96"] for a in items)}
    report={"experiment":"ENGINE001_ANILINES_V24_NATIVE_FOOTPRINT_PROVENANCE",
            "status":"OFFLINE_NATIVE_BLANK_VERIFIED_NOT_GAME",
            "source_sha256":v22_report["source_sha256"],"v22_report_sha256":digest(v22/"report.json"),
            "v23_report_sha256":digest(v23/"report.json"),
            "blank":observed["blank"],"engineVersion":native["engineVersion"],
            "browserCapabilities":observed["browserCapabilities"],
            "nativeGL":native["glInfo"],
            "metrics":{"vertex":aggregate(result[:56]),"link":aggregate(result[56:]),
                       "baseline_source_support":5812,
                       "blank_alpha_pixels":0,"native_cases_reproduced":89},
            "geometry_modified":False,"artifacts_sha256":files,
            "not_tested":["true owner mask","live input","game CHALK","E5","production"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for option in ("workspace","v22","v23","source","ani","output"):
        p.add_argument("--"+option,required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.workspace,a.v22,a.v23,a.source,a.ani,a.output)["metrics"],indent=2))
