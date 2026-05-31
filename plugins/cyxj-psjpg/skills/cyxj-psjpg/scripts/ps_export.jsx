// ps_export.jsx
// 用真 Photoshop 把源目录里的所有 png/jpg/jpeg 导出为同名 JPG。
// 参数（源目录 / 输出目录 / 质量）从 /tmp/cyxj_psjpg_cfg.txt 读取，每行一个，
// 由 psjpg.sh 写入——这样 JSX 本身保持静态、无需在运行时改动即可复用。
// 导出参数：质量可配 + Progressive 3 Scans + 嵌 sRGB（最贴近手动 Export As）。

#target photoshop

// ---- 读取配置（UTF-8，支持中文路径）----
var cfg = new File("/tmp/cyxj_psjpg_cfg.txt");
cfg.encoding = "UTF8";
cfg.open("r");
var raw = cfg.read();
cfg.close();
var lines = raw.replace(/\r/g, "").split("\n");
var srcDir = lines[0];
var outDir = lines[1];
var QUALITY = parseInt(lines[2], 10);
if (isNaN(QUALITY) || QUALITY < 1 || QUALITY > 12) QUALITY = 12;

var outFolder = new Folder(outDir);
if (!outFolder.exists) outFolder.create();

// ---- 日志 ----
// 用显式 "\n" 写换行（不用 writeln：它在 PS 里默认写 Mac 老式 \r，会让整个日志挤成一行，
// 导致 psjpg.sh 里 grep '^\[OK' 锚定行首匹配不到、成功数误报为 0）。
var logFile = new File("/tmp/cyxj_psjpg_export.log");
logFile.open("w");
logFile.write("Start: " + (new Date()).toString() + "\n");
logFile.write("Src: " + srcDir + "\n");
logFile.write("Out: " + outDir + "\n");
logFile.write("Quality: " + QUALITY + " (Progressive 3 Scans)\n");
logFile.close();
function log(msg) {
    logFile.open("a");
    logFile.write(msg + "\n");
    logFile.close();
}

// ---- 收集源文件 ----
var srcFolder = new Folder(srcDir);
var files = srcFolder.getFiles(function(f) {
    return (f instanceof File) && /\.(png|jpe?g)$/i.test(f.name);
});
log("Found: " + files.length + " files");

// ---- Save As JPEG 配置 ----
var saveOpts = new JPEGSaveOptions();
saveOpts.quality = QUALITY;
saveOpts.embedColorProfile = true;
saveOpts.formatOptions = FormatOptions.PROGRESSIVE;
saveOpts.scans = 3;
saveOpts.matte = MatteType.NONE;

var success = 0, failed = 0;
for (var i = 0; i < files.length; i++) {
    var srcFile = files[i];
    var baseName = srcFile.name.replace(/\.[^.]+$/, "");
    var outFile = new File(outDir + "/" + baseName + ".jpg");
    try {
        var doc = app.open(srcFile);
        doc.saveAs(outFile, saveOpts, true, Extension.LOWERCASE);
        doc.close(SaveOptions.DONOTSAVECHANGES);
        success++;
        log("[OK " + (i + 1) + "/" + files.length + "] " + srcFile.name + " -> " + baseName + ".jpg");
    } catch (e) {
        failed++;
        log("[FAIL " + (i + 1) + "/" + files.length + "] " + srcFile.name + " - " + e.toString());
        try { if (app.documents.length > 0) app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
    }
}
log("Done. Success: " + success + ", Failed: " + failed);
log("End: " + (new Date()).toString());
