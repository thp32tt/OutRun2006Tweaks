// ExportOutRunMap.java
// Ghidra post-analysis script: exports a stable, queryable map of OR2006C2C.EXE.
// @category OutRun2006Tweaks

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.symbol.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

public class ExportOutRunMap extends GhidraScript {
    private File outDir;
    private Address imageBase;
    private boolean doDecompile = true;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            throw new IllegalArgumentException("usage: ExportOutRunMap.java <output-dir> [nodecompile]");
        }
        outDir = new File(args[0]).getCanonicalFile();
        if (args.length > 1 && "nodecompile".equalsIgnoreCase(args[1])) {
            doDecompile = false;
        }
        if (!outDir.exists() && !outDir.mkdirs()) {
            throw new IOException("cannot create output directory: " + outDir);
        }

        imageBase = currentProgram.getImageBase();
        println("OutRun map export -> " + outDir);
        exportManifest();
        exportFunctionsAndDecompile();
        exportInstructionsCallsAndXrefs();
        exportStrings();
        exportSymbols();
        println("OutRun map export complete.");
    }

    private BufferedWriter writer(String name) throws IOException {
        return new BufferedWriter(new OutputStreamWriter(
            new FileOutputStream(new File(outDir, name)), StandardCharsets.UTF_8), 1 << 20);
    }

    private long rva(Address address) {
        return address.subtract(imageBase);
    }

    private String hex(Address address) {
        return "0x" + Long.toHexString(address.getOffset()).toUpperCase(Locale.ROOT);
    }

    private String rvaHex(Address address) {
        return String.format(Locale.ROOT, "0x%08X", rva(address));
    }

    private static String q(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder(s.length() + 16);
        b.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\b': b.append("\\b"); break;
                case '\f': b.append("\\f"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format(Locale.ROOT, "\\u%04x", (int)c));
                    else b.append(c);
            }
        }
        return b.append('"').toString();
    }

    private static String bytesHex(byte[] data) {
        StringBuilder b = new StringBuilder(data.length * 2);
        for (byte x : data) b.append(String.format(Locale.ROOT, "%02x", x & 0xff));
        return b.toString();
    }

    private String sha256Executable() {
        try {
            String path = currentProgram.getExecutablePath();
            if (path == null || path.isEmpty()) return "";
            File f = new File(path);
            if (!f.isFile()) return "";
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new BufferedInputStream(new FileInputStream(f))) {
                byte[] buf = new byte[1 << 20];
                for (int n; (n = in.read(buf)) > 0;) md.update(buf, 0, n);
            }
            return bytesHex(md.digest());
        } catch (Exception e) {
            return "";
        }
    }

    private void exportManifest() throws IOException {
        try (BufferedWriter w = writer("manifest.json")) {
            w.write("{\n");
            w.write("  \"schemaVersion\": 1,\n");
            w.write("  \"program\": " + q(currentProgram.getName()) + ",\n");
            w.write("  \"executablePath\": " + q(currentProgram.getExecutablePath()) + ",\n");
            w.write("  \"sha256\": " + q(sha256Executable()) + ",\n");
            w.write("  \"language\": " + q(currentProgram.getLanguageID().toString()) + ",\n");
            w.write("  \"compilerSpec\": " + q(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) + ",\n");
            w.write("  \"imageBase\": " + q(hex(imageBase)) + ",\n");
            w.write("  \"minAddress\": " + q(hex(currentProgram.getMinAddress())) + ",\n");
            w.write("  \"maxAddress\": " + q(hex(currentProgram.getMaxAddress())) + ",\n");
            w.write("  \"decompiled\": " + doDecompile + "\n");
            w.write("}\n");
        }
    }

    private void exportFunctionsAndDecompile() throws Exception {
        DecompInterface decomp = null;
        BufferedWriter dw = null;
        if (doDecompile) {
            decomp = new DecompInterface();
            decomp.setOptions(new DecompileOptions());
            decomp.toggleCCode(true);
            decomp.toggleSyntaxTree(false);
            if (!decomp.openProgram(currentProgram)) {
                throw new IllegalStateException("decompiler could not open program");
            }
            dw = writer("decompile.jsonl");
        }

        try (BufferedWriter fw = writer("functions.jsonl")) {
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                Address entry = f.getEntryPoint();
                Address min = f.getBody().getMinAddress();
                Address max = f.getBody().getMaxAddress();
                String sig;
                try { sig = f.getPrototypeString(true, true); }
                catch (Exception e) { sig = f.getName(); }

                fw.write("{\"entry\":" + q(hex(entry)) +
                    ",\"rva\":" + q(rvaHex(entry)) +
                    ",\"name\":" + q(f.getName()) +
                    ",\"namespace\":" + q(f.getParentNamespace().getName()) +
                    ",\"min\":" + q(hex(min)) +
                    ",\"max\":" + q(hex(max)) +
                    ",\"bodySize\":" + f.getBody().getNumAddresses() +
                    ",\"thunk\":" + f.isThunk() +
                    ",\"external\":" + f.isExternal() +
                    ",\"signature\":" + q(sig) + "}\n");

                if (dw != null && !f.isExternal()) {
                    DecompileResults dr = decomp.decompileFunction(f, 90, monitor);
                    String c = "";
                    boolean complete = dr != null && dr.decompileCompleted();
                    if (complete && dr.getDecompiledFunction() != null) {
                        c = dr.getDecompiledFunction().getC();
                    }
                    dw.write("{\"entry\":" + q(hex(entry)) +
                        ",\"rva\":" + q(rvaHex(entry)) +
                        ",\"name\":" + q(f.getName()) +
                        ",\"complete\":" + complete +
                        ",\"c\":" + q(c) + "}\n");
                }
            }
        } finally {
            if (dw != null) dw.close();
            if (decomp != null) decomp.dispose();
        }
    }

    private void exportInstructionsCallsAndXrefs() throws IOException, MemoryAccessException {
        Set<String> seenXrefs = new HashSet<>();
        try (BufferedWriter iw = writer("instructions.jsonl");
             BufferedWriter cw = writer("calls.jsonl");
             BufferedWriter xw = writer("xrefs.jsonl")) {
            Listing listing = currentProgram.getListing();
            InstructionIterator it = listing.getInstructions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Instruction ins = it.next();
                Address a = ins.getAddress();
                Function f = listing.getFunctionContaining(a);
                StringBuilder text = new StringBuilder(ins.getMnemonicString());
                for (int i = 0; i < ins.getNumOperands(); i++) {
                    text.append(i == 0 ? " " : ", ");
                    text.append(ins.getDefaultOperandRepresentation(i));
                }
                iw.write("{\"address\":" + q(hex(a)) +
                    ",\"rva\":" + q(rvaHex(a)) +
                    ",\"functionRva\":" + (f == null ? "null" : q(rvaHex(f.getEntryPoint()))) +
                    ",\"mnemonic\":" + q(ins.getMnemonicString()) +
                    ",\"text\":" + q(text.toString()) +
                    ",\"bytes\":" + q(bytesHex(ins.getBytes())) + "}\n");

                Reference[] refs = ins.getReferencesFrom();
                for (Reference ref : refs) {
                    Address to = ref.getToAddress();
                    if (to == null) continue;
                    RefType rt = ref.getReferenceType();
                    String targetRva = currentProgram.getMemory().contains(to) ? rvaHex(to) : null;
                    String key = a + "|" + to + "|" + rt;
                    if (seenXrefs.add(key)) {
                        xw.write("{\"from\":" + q(hex(a)) +
                            ",\"fromRva\":" + q(rvaHex(a)) +
                            ",\"to\":" + q(hex(to)) +
                            ",\"toRva\":" + q(targetRva) +
                            ",\"type\":" + q(rt.getName()) +
                            ",\"source\":" + q(ref.getSource().toString()) + "}\n");
                    }
                    if (rt.isCall()) {
                        Function target = currentProgram.getFunctionManager().getFunctionAt(to);
                        cw.write("{\"site\":" + q(hex(a)) +
                            ",\"siteRva\":" + q(rvaHex(a)) +
                            ",\"callerRva\":" + (f == null ? "null" : q(rvaHex(f.getEntryPoint()))) +
                            ",\"target\":" + q(hex(to)) +
                            ",\"targetRva\":" + q(targetRva) +
                            ",\"targetName\":" + q(target == null ? null : target.getName()) + "}\n");
                    }
                }
            }
        }
    }

    private void exportStrings() throws IOException {
        try (BufferedWriter w = writer("strings.jsonl")) {
            DataIterator it = currentProgram.getListing().getDefinedData(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Data d = it.next();
                Object v = d.getValue();
                if (!(v instanceof String)) continue;
                Address a = d.getAddress();
                String s = (String)v;
                w.write("{\"address\":" + q(hex(a)) +
                    ",\"rva\":" + q(rvaHex(a)) +
                    ",\"length\":" + s.length() +
                    ",\"value\":" + q(s) + "}\n");
            }
        }
    }

    private void exportSymbols() throws IOException {
        try (BufferedWriter w = writer("symbols.jsonl")) {
            SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Symbol s = it.next();
                Address a = s.getAddress();
                boolean inMem = a != null && currentProgram.getMemory().contains(a);
                w.write("{\"name\":" + q(s.getName()) +
                    ",\"address\":" + q(a == null ? null : hex(a)) +
                    ",\"rva\":" + q(inMem ? rvaHex(a) : null) +
                    ",\"type\":" + q(s.getSymbolType().toString()) +
                    ",\"namespace\":" + q(s.getParentNamespace().getName()) +
                    ",\"source\":" + q(s.getSource().toString()) + "}\n");
            }
        }
    }
}
