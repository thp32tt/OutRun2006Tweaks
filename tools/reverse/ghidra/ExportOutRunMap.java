// ExportOutRunMap.java
// @category OutRun.Reverse
// @description Export deterministic whole-program reverse-engineering records for OR2006C2C.EXE.

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.address.AddressRangeIterator;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.RefType;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

public class ExportOutRunMap extends GhidraScript {
    private long imageBase;
    private FunctionManager fm;
    private Listing listing;

    private static String esc(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\\': b.append("\\\\"); break;
                case '"': b.append("\\\""); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int)c));
                    else b.append(c);
            }
        }
        return b.toString();
    }

    private static String q(String s) { return "\"" + esc(s) + "\""; }
    private static String hex(long v) { return String.format("0x%08X", v); }

    private String addr(Address a) {
        if (a == null || !a.isMemoryAddress()) return null;
        return hex(a.getOffset());
    }

    private String rva(Address a) {
        if (a == null || !a.isMemoryAddress()) return null;
        if (!currentProgram.getMemory().contains(a)) return null;
        return hex(a.getOffset() - imageBase);
    }

    private String addressSpace(Address a) {
        return a == null ? null : a.getAddressSpace().getName();
    }

    private String json(Map<String, Object> m) {
        StringBuilder b = new StringBuilder();
        b.append('{');
        boolean first = true;
        for (Map.Entry<String, Object> e : m.entrySet()) {
            if (!first) b.append(',');
            first = false;
            b.append(q(e.getKey())).append(':');
            Object v = e.getValue();
            if (v == null) b.append("null");
            else if (v instanceof Number || v instanceof Boolean) b.append(v.toString());
            else b.append(q(v.toString()));
        }
        b.append('}');
        return b.toString();
    }

    private BufferedWriter out(File dir, String name) throws IOException {
        return new BufferedWriter(new FileWriter(new File(dir, name), false), 1024 * 1024);
    }

    private String functionEntry(Address a) {
        Function f = fm.getFunctionContaining(a);
        return f == null ? null : rva(f.getEntryPoint());
    }

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("usage: ExportOutRunMap.java <output-dir>");

        File dir = new File(args[0]);
        if (!dir.exists() && !dir.mkdirs()) throw new IOException("cannot create output directory: " + dir);

        imageBase = currentProgram.getImageBase().getOffset();
        fm = currentProgram.getFunctionManager();
        listing = currentProgram.getListing();

        exportProgram(dir);
        exportFunctions(dir);
        exportInstructionsCallsAndXrefs(dir);
        exportStrings(dir);
        exportImports(dir);
        println("OUTRUN_MAP_EXPORT_COMPLETE=" + dir.getAbsolutePath());
    }

    private void exportProgram(File dir) throws IOException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("program_name", currentProgram.getName());
        m.put("executable_path", currentProgram.getExecutablePath());
        m.put("sha256", currentProgram.getExecutableSHA256());
        m.put("md5", currentProgram.getExecutableMD5());
        m.put("image_base", hex(imageBase));
        m.put("language", currentProgram.getLanguageID().toString());
        m.put("compiler", currentProgram.getCompiler());
        m.put("format", currentProgram.getExecutableFormat());
        m.put("function_count", fm.getFunctionCount());
        try (BufferedWriter w = out(dir, "program.jsonl")) {
            w.write(json(m)); w.newLine();
        }
    }

    private void exportFunctions(File dir) throws IOException {
        try (BufferedWriter w = out(dir, "functions.jsonl");
             BufferedWriter rw = out(dir, "function_ranges.jsonl")) {
            FunctionIterator it = fm.getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                AddressSetView body = f.getBody();
                String entryRva = rva(f.getEntryPoint());
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("entry_va", addr(f.getEntryPoint()));
                m.put("entry_rva", entryRva);
                m.put("name", f.getName());
                m.put("namespace", f.getParentNamespace() == null ? "" : f.getParentNamespace().getName(true));
                m.put("size", body == null ? 0 : body.getNumAddresses());
                m.put("body_min_rva", body == null || body.isEmpty() ? null : rva(body.getMinAddress()));
                m.put("body_max_rva", body == null || body.isEmpty() ? null : rva(body.getMaxAddress()));
                m.put("thunk", f.isThunk());
                m.put("external", f.isExternal());
                m.put("calling_convention", f.getCallingConventionName());
                m.put("parameter_count", f.getParameterCount());
                m.put("return_type", f.getReturnType() == null ? "" : f.getReturnType().getDisplayName());
                w.write(json(m)); w.newLine();

                if (body != null && !body.isEmpty() && entryRva != null) {
                    int rangeIndex = 0;
                    AddressRangeIterator ranges = body.getAddressRanges();
                    while (ranges.hasNext()) {
                        AddressRange range = ranges.next();
                        String startRva = rva(range.getMinAddress());
                        String endRva = rva(range.getMaxAddress());
                        if (startRva == null || endRva == null) continue;
                        Map<String, Object> rm = new LinkedHashMap<>();
                        rm.put("entry_rva", entryRva);
                        rm.put("range_index", rangeIndex++);
                        rm.put("start_rva", startRva);
                        rm.put("end_rva", endRva);
                        rw.write(json(rm)); rw.newLine();
                    }
                }
            }
        }
    }

    private void exportInstructionsCallsAndXrefs(File dir) throws IOException {
        try (BufferedWriter iw = out(dir, "instructions.jsonl");
             BufferedWriter cw = out(dir, "calls.jsonl");
             BufferedWriter xw = out(dir, "xrefs.jsonl")) {
            InstructionIterator it = listing.getInstructions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Instruction ins = it.next();
                Address a = ins.getAddress();
                Map<String, Object> im = new LinkedHashMap<>();
                im.put("va", addr(a));
                im.put("rva", rva(a));
                im.put("function_rva", functionEntry(a));
                im.put("mnemonic", ins.getMnemonicString());
                im.put("text", ins.toString());
                im.put("bytes", bytesHex(ins));
                iw.write(json(im)); iw.newLine();

                Reference[] refs = ins.getReferencesFrom();
                if (refs == null) continue;
                for (Reference ref : refs) {
                    Address to = ref.getToAddress();
                    RefType rt = ref.getReferenceType();
                    Map<String, Object> xm = new LinkedHashMap<>();
                    xm.put("from_rva", rva(a));
                    xm.put("from_space", addressSpace(a));
                    xm.put("from_function_rva", functionEntry(a));
                    xm.put("to_va", addr(to));
                    xm.put("to_rva", rva(to));
                    xm.put("to_space", addressSpace(to));
                    xm.put("to_function_rva", to != null && to.isMemoryAddress() ? functionEntry(to) : null);
                    xm.put("type", rt == null ? "" : rt.getName());
                    xm.put("primary", ref.isPrimary());
                    xw.write(json(xm)); xw.newLine();

                    if (rt != null && rt.isCall()) {
                        Map<String, Object> cm = new LinkedHashMap<>();
                        cm.put("callsite_rva", rva(a));
                        cm.put("caller_rva", functionEntry(a));
                        cm.put("callee_va", addr(to));
                        cm.put("callee_rva", rva(to));
                        cm.put("callee_space", addressSpace(to));
                        cm.put("callee_function_rva", to != null && to.isMemoryAddress() ? functionEntry(to) : null);
                        cm.put("type", rt.getName());
                        cw.write(json(cm)); cw.newLine();
                    }
                }
            }
        }
    }

    private String bytesHex(Instruction ins) {
        try {
            byte[] bytes = ins.getBytes();
            StringBuilder b = new StringBuilder(bytes.length * 2);
            for (byte x : bytes) b.append(String.format("%02x", x & 0xff));
            return b.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private void exportStrings(File dir) throws IOException {
        try (BufferedWriter w = out(dir, "strings.jsonl")) {
            DataIterator it = listing.getDefinedData(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Data d = it.next();
                Object value;
                try { value = d.getValue(); } catch (Exception e) { continue; }
                if (!(value instanceof String)) continue;
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("va", addr(d.getAddress()));
                m.put("rva", rva(d.getAddress()));
                m.put("function_rva", functionEntry(d.getAddress()));
                m.put("datatype", d.getDataType() == null ? "" : d.getDataType().getDisplayName());
                m.put("length", d.getLength());
                m.put("value", value.toString());
                w.write(json(m)); w.newLine();
            }
        }
    }

    private void exportImports(File dir) throws IOException {
        try (BufferedWriter w = out(dir, "imports.jsonl")) {
            FunctionIterator it = fm.getExternalFunctions();
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("name", f.getName());
                m.put("namespace", f.getParentNamespace() == null ? "" : f.getParentNamespace().getName(true));
                m.put("entry_va", addr(f.getEntryPoint()));
                m.put("entry_rva", rva(f.getEntryPoint()));
                m.put("calling_convention", f.getCallingConventionName());
                w.write(json(m)); w.newLine();
            }
        }
    }
}
