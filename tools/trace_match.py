import sys
import re

memory_trace = ''
llvm_ir = ''

with open(sys.argv[1], 'r') as trace_file:
    line = trace_file.readline()

    while line:
        memory_trace += line
        line = trace_file.readline()

with open(sys.argv[2], 'r') as ir_file:
    line = ir_file.readline()

    while line:
        llvm_ir += line
        line = ir_file.readline()


# Regex patterns for parsing
mem_trace_regex = re.compile(r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+)(?: #/[\w/\.]+:(\d+))? ! (LOAD|STORE)")
llvm_dbg_regex = re.compile(r"!dbg !(\d+)")
llvm_line_info_regex = re.compile(r"!(\d+) = !DILocation\(line: (\d+),")

# Parse memory trace
trace_info = {}
trace_lines = memory_trace.strip().split('\n')
for line in trace_lines:
    match = mem_trace_regex.search(line)
    if match:
        inst_addr = match.group(1)
        mem_addr = match.group(2)
        line_number = match.group(3) or "Unknown"
        operation = match.group(4)
        if line_number not in trace_info:
            trace_info[line_number] = []
        trace_info[line_number].append({
            'mem_addr': mem_addr,
            'operation': operation
        })


# Parse LLVM IR
llvm_info = {}
llvm_lines = llvm_ir.strip().split('\n')
for line in llvm_lines:
    dbg_match = llvm_dbg_regex.search(line)
    if dbg_match:
        dbg_id = dbg_match.group(1)
        for info_line in llvm_lines:
            line_info_match = llvm_line_info_regex.match(info_line)
            if line_info_match and line_info_match.group(1) == dbg_id:
                line_number = line_info_match.group(2)
                #print(line_number)
                if("load" in line or "store" in line):
                    llvm_info.setdefault(line_number, []).append(line)

# Match and output results
for line_number in sorted(trace_info.keys()):
    print(f"Source Line {line_number}:")
    print("Memory Trace:")
    for trace in trace_info.get(line_number, []):
        print(trace)
        print("LLVM Instructions:")
    for llvm in llvm_info.get(line_number, []):
        print(llvm)
    print("\n")
