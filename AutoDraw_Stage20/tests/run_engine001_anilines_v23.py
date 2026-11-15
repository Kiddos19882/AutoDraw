#!/usr/bin/env python3
"""V23: browser-native Egret width1 footprint on frozen V22 cases; not live game."""
import argparse,base64,hashlib,json,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ANI_SHA="2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def make_fixtures(verts,links):
    def logical(point):
        x,y=point
        if not (type(x) is int and type(y) is int and 0<=x<200 and 0<=y<320):
            raise ValueError("Invalid source point")
        return {"x":x*.75+155,"y":y*.75}
    fixtures=[]
    for index,v in enumerate(verts):
        xy=v["source_xy"];pt=logical(xy)
        fixtures.append({"id":f"vertex-{index:03d}","kind":"vertex",
                         "sourcePoints":[xy,xy],"points":[pt,pt]})
    for index,v in enumerate(links):
        a,b=v["source_start"],v["source_end"]
        if max(abs(a[0]-b[0]),abs(a[1]-b[1]))!=1:
            raise ValueError("Link is not source-adjacent")
        fixtures.append({"id":f"link-{index:03d}","kind":"link",
                         "sourcePoints":[a,b],"points":[logical(a),logical(b)],
                         "centerMixed":bool(v["mixed_center_classes"])})
    if sum(f.get("centerMixed",False) for f in fixtures)!=9:
        raise ValueError("V22 cross-class link count mismatch")
    return fixtures

def check_input(root,source,anilines):
    report=json.loads((root/"report.json").read_text(encoding="utf8"))
    if (report.get("source_sha256")!=SOURCE_SHA or
        report.get("anilines_sha256")!=ANI_SHA or
        digest(source)!=SOURCE_SHA or digest(anilines)!=ANI_SHA):
        raise ValueError("V23 source/V22 provenance mismatch")
    for name,expected in report["derived_sha256"].items():
        if digest(root/name)!=expected:raise ValueError("V22 artifact checksum mismatch "+name)
    m=report["metrics"]
    if not (m["ambiguous_components"]==23 and
            m["vertex_profiles"]["count"]==56 and m["link_profiles"]["count"]==33 and
            m["frozen_v20_supported"]==m["frozen_v21_supported"]==5812):
        raise ValueError("V22 frozen original population differs")
    verts=json.loads((root/"vertex-profiles.json").read_text(encoding="utf8"))
    links=json.loads((root/"link-profiles.json").read_text(encoding="utf8"))
    if len(verts)!=56 or len(links)!=33:raise ValueError("Missing cases")
    with Image.open(root/"quantized-palette-labels.png") as im:
        palette=list(map(list, __import__("numpy").asarray(im.convert("L"),dtype="uint8")))
    if len(palette)!=240 or any(len(row)!=150 for row in palette):
        raise ValueError("V22 palette dimensions changed")
    fixtures=make_fixtures(verts,links)
    return fixtures,palette,report

def browser_measure(workspace,fixtures,palette):
    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):
            super().__init__(*a,directory=str(workspace),**kw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),QuietHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    driver=None
    try:
        opts=Options();opts.add_argument("-headless")
        opts.set_preference("webgl.disabled",False)
        opts.set_preference("webgl.force-enabled",True)
        opts.set_preference("webgl.enable-webgl2",True)
        driver=webdriver.Firefox(options=opts)
        driver.set_page_load_timeout(180)
        driver.set_script_timeout(600)
        url=f"http://127.0.0.1:{server.server_port}/AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope"
        driver.get(url)
        WebDriverWait(driver,120).until(
            lambda d:d.execute_script("return document.body.dataset.twoIconStatus")=="ready")
        output=driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderV23Width1Footprints(arguments[0],arguments[1]);",
            fixtures,palette)
        if output.get("schema")!="ENGINE001_V23_WIDTH1_NATIVE_OFFLINE":
            raise ValueError("Wrong V23 native renderer schema")
        output["browserCapabilities"]={"browser":driver.capabilities.get("browserName"),
                                        "version":driver.capabilities.get("browserVersion")}
        return output
    finally:
        if driver:driver.quit()
        server.shutdown();server.server_close();thread.join(timeout=5)

def run(workspace,v22,source,anilines,output):
    fixtures,palette,original=check_input(v22,source,anilines)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Cannot overwrite frozen V23 evidence")
    result=browser_measure(workspace,fixtures,palette)
    cases=result["cases"]
    if len(cases)!=89 or result["vertexCount"]!=56 or result["linkCount"]!=33:
        raise ValueError("Wrong native case count")
    if any(c["id"]!=f["id"] or c["kind"]!=f["kind"] for c,f in zip(cases,fixtures)):
        raise ValueError("Native fixture order mismatch")
    if set(result["representativePngDataUrls"])!={"vertex","link-uniform","link-mixed"}:
        raise ValueError("Missing deterministically selected native examples")
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name,data_url in result.pop("representativePngDataUrls").items():
        if not data_url.startswith("data:image/png;base64,"):
            raise ValueError("Native PNG not returned")
        binary=base64.b64decode(data_url.partition(",")[2],validate=True)
        file=out/(name+".png");file.write_bytes(binary)
        with Image.open(BytesIO(binary)) as image:
            if image.size!=(1380,720):raise ValueError("Unexpected native PNG size")
        hashes[file.name]=digest(file)
    (out/"cases.json").write_text(json.dumps(cases,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    hashes["cases.json"]=digest(out/"cases.json")
    def totals(items):
        return {"count":len(items),
                "no_raster_cases":sum(c["coverage"]["128"]["alphaPixels"]==0 for c in items),
                "cross_proxy_cases":sum(c["coverage"]["128"]["foreignClassPixels"]>0 for c in items),
                "alpha_pixels_128":sum(c["coverage"]["128"]["alphaPixels"] for c in items),
                "foreign_proxy_pixels_128":sum(c["coverage"]["128"]["foreignClassPixels"] for c in items),
                "outside_roi_alpha_pixels_128":sum(c["coverage"]["128"]["outsideRoiPixels"] for c in items),
                "canvas2d_vs_webgl_diff_cases":sum(not c["canvas2dVsWebgl"]["equal"] for c in items)}
    vert=[c for c in cases if c["kind"]=="vertex"]
    links=[c for c in cases if c["kind"]=="link"]
    report={"experiment":"ENGINE001_ANILINES_V23_NATIVE_WIDTH1_FOOTPRINT",
            "status":"OFFLINE_ARCHIVED_NATIVE_EGRET_NOT_LIVE_GAME",
            "original_v22_source_sha256":original["source_sha256"],
            "original_v22_artifact_report_sha256":digest(v22/"report.json"),
            "source_sha256":SOURCE_SHA,"anilines_sha256":ANI_SHA,
            "baseline_supported_source_pixels":5812,"geometry_modified":False,
            "engineVersion":result["engineVersion"],
            "browser":result["browser"],"browserCapabilities":result["browserCapabilities"],
            "nativeGL":result["glInfo"],"rasterScale":3,
            "metrics":{"vertices":totals(vert),
                       "links":totals(links),
                       "link_center_uniform":totals(links[:0]+[c for c,f in zip(cases,fixtures) if f["kind"]=="link" and not f["centerMixed"]]),
                       "link_center_mixed":totals([c for c,f in zip(cases,fixtures) if f["kind"]=="link" and f["centerMixed"]])},
            "artifacts_sha256":hashes,
            "not_tested":["actual live game input","run-bound exact CHALK",
                          "true color/semantic owner","production quality","E5"]}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,default=Path("."))
    p.add_argument("--v22",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--anilines",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=run(args.workspace,args.v22,args.source,args.anilines,args.output)
    print(json.dumps(data["metrics"],indent=2))
