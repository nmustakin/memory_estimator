/*
 * Copyright (C) 2009-2021 Intel Corporation.
 * SPDX-License-Identifier: MIT
 */

/*
 * Sample buffering tool
 *
 * This tool collects an address trace of instructions that access memory
 * by filling a buffer.  When the buffer overflows,the callback writes all
 * of the collected records to a file.
 *
 */

#define MAX_THREADS 64
#define MAX_SPLIT 1000

#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cstddef>
#include <unistd.h>
#include <unordered_map>
#include <vector>
#include "pin.H"
using std::cerr;
using std::endl;
using std::hex;
using std::ifstream;
using std::ofstream;
using std::ostringstream; 
using std::string;
using std::unordered_map;
using std::vector; 
//using std::cout; 
/*
 * Global variables
*/
UINT32 GlobalObservationCount[MAX_THREADS];
UINT32 ObservationCount_perThread[MAX_THREADS][MAX_SPLIT];
unordered_map<ADDRINT, UINT32> MemoryUsage[MAX_THREADS][MAX_SPLIT];
unordered_map<ADDRINT, UINT32> allThreadMap;
string outputFileNamePrefix; 
ofstream outputFile;
/*
 * Name of the output file
 */
KNOB< string > KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "buffer.out", "output file");
KNOB< UINT32 > KnobSamplingInterval(KNOB_MODE_WRITEONCE, "pintool", "i", "100", "Sampling Interval");
KNOB< UINT32 > KnobNumSplits(KNOB_MODE_WRITEONCE, "pintool", "s", "100", "Number of sample splits");
KNOB< UINT32 > KnobSampleReplication(KNOB_MODE_WRITEONCE, "pintool", "r", "10", "Frequency of sample replication");

/*
 * The ID of the buffer
 */
BUFFER_ID bufId;

/*
 * Thread specific data
 */
TLS_KEY mlog_key;

/*
 * Number of OS pages for the buffer
 */
#define NUM_BUF_PAGES 1024

struct MEMREF
{
    ADDRINT pc;
    ADDRINT ea;
    UINT32 size;
    BOOL read;
};

// 32‑bit seed kept per thread (TLS or array indexed by tid)
static UINT32 seed[MAX_THREADS];

static inline UINT32 PIN_FAST_ANALYSIS_CALL
lcg_step(UINT32 &s)
{
    __asm__ __volatile__(
        "imull $1664525, %[s]\n\t"
        "add   $1013904223, %[s]\n\t"
        : [s] "+r"(s)      // input + output
        :                  // no extra inputs
        : "cc"             // clobbers condition codes only
    );
    return s;
}

static inline ADDRINT PIN_FAST_ANALYSIS_CALL
ShouldSample(THREADID tid, UINT32 rate)
{
    return ((lcg_step(seed[tid]) & rate) == 0)? 1: 0;
}

VOID Trace(TRACE trace, VOID* v)
{
    for (BBL bbl = TRACE_BblHead(trace); BBL_Valid(bbl); bbl = BBL_Next(bbl))
    {
        for (INS ins = BBL_InsHead(bbl); INS_Valid(ins); ins = INS_Next(ins))
        {
            if (!INS_IsStandardMemop(ins) && !INS_HasMemoryVector(ins))
            {
                // We don't know how to treat these instructions
                continue;
            }

            UINT32 memoryOperands = INS_MemoryOperandCount(ins);

            for (UINT32 memOp = 0; memOp < memoryOperands; memOp++)
            {
                UINT32 refSize = INS_MemoryOperandSize(ins, memOp);

                // Note that if the operand is both read and written we log it once
                // for each.
                if (INS_MemoryOperandIsRead(ins, memOp))
                {
                    INS_InsertIfCall(ins, IPOINT_BEFORE, AFUNPTR(ShouldSample),
                        IARG_FAST_ANALYSIS_CALL,
                        IARG_THREAD_ID,
                        IARG_UINT32, KnobSamplingInterval.Value() - 1,
                        IARG_END);
                    INS_InsertFillBufferThen(ins, IPOINT_BEFORE, bufId, IARG_INST_PTR, offsetof(struct MEMREF, pc), IARG_MEMORYOP_EA,
                                         memOp, offsetof(struct MEMREF, ea), IARG_UINT32, refSize, offsetof(struct MEMREF, size),
                                         IARG_BOOL, TRUE, offsetof(struct MEMREF, read), IARG_END);
                }

                if (INS_MemoryOperandIsWritten(ins, memOp))
                {
                    INS_InsertIfCall(ins, IPOINT_BEFORE, AFUNPTR(ShouldSample),
                        IARG_FAST_ANALYSIS_CALL,
                        IARG_THREAD_ID,
                        IARG_UINT32, KnobSamplingInterval.Value() - 1,
                        IARG_END);
                    INS_InsertFillBufferThen(ins, IPOINT_BEFORE, bufId, IARG_INST_PTR, offsetof(struct MEMREF, pc), IARG_MEMORYOP_EA,
                                         memOp, offsetof(struct MEMREF, ea), IARG_UINT32, refSize, offsetof(struct MEMREF, size),
                                         IARG_BOOL, FALSE, offsetof(struct MEMREF, read), IARG_END);
                }
            }
        }
    }
}

/*!
 * Called when a buffer fills up, or the thread exits, so we can process it or pass it off
 * as we see fit.
 * @param[in] id		buffer handle
 * @param[in] tid		id of owning thread
 * @param[in] ctxt		application context
 * @param[in] buf		actual pointer to buffer
 * @param[in] numElements	number of records
 * @param[in] v			callback value
 * @return  A pointer to the buffer to resume filling.
 */
VOID* BufferFull(BUFFER_ID id, THREADID tid, const CONTEXT* ctxt, VOID* buf, UINT64 numElements, VOID* v)
{
    struct MEMREF* reference = (struct MEMREF*)buf;
    UINT32 replication = KnobSampleReplication.Value();
    
    for (UINT64 i = 0; i < numElements; i++, reference++)
    {
        UINT32 address = reference->ea; 
        UINT32 size = reference->size; 
        if (address != 0) {
            GlobalObservationCount[tid]++;
            for(UINT32 j = 0; j < replication; j++){
                UINT32 bin = lcg_step(seed[tid]) % KnobNumSplits.Value();
                MemoryUsage[tid][bin][address] = (MemoryUsage[tid][bin][address]>size)? MemoryUsage[tid][bin][address] : size;
                ++ObservationCount_perThread[tid][bin];
                //cout << "Replicated: " << j << "at bin: "<< bin << endl;
            }
        }
    }

    return buf;
}

VOID ThreadStart(THREADID tid, CONTEXT* ctxt, INT32 flags, VOID* v)
{
    UINT32 PID = PIN_GetPid();
    seed[tid] = PID * 31 + tid * 19;
}

VOID ThreadFini(THREADID tid, const CONTEXT* ctxt, INT32 code, VOID* v)
{
    return;
}

string GetOutputFileName() {
    ifstream cmdline("/proc/self/cmdline");
    string binaryName;
    vector<string> args;

    int pid = PIN_GetPid();

    if (cmdline) {
        string arg;
        while (std::getline(cmdline, arg, '\0')) {
            if (binaryName.empty()) {
                binaryName = arg;  // First entry is the binary name
            } else {
                args.push_back(arg);  // Remaining are arguments
            }
        }
    }

    // Extract only the binary name (remove the full path)
    size_t lastSlash = binaryName.find_last_of('/');
    if (lastSlash != string::npos) {
        binaryName = binaryName.substr(lastSlash + 1);
    }

    // Construct parameter string
    std::ostringstream paramStream;
    for (const auto &arg : args) {
        paramStream << arg << "_";
    }

    string paramStr = paramStream.str();
    if (!paramStr.empty()) {
        paramStr.pop_back();  // Remove trailing underscore
    }

    // Construct final filename
    std::ostringstream filename;
    const UINT32 samplingRate = KnobSamplingInterval.Value();
    filename << "traces/Buffered_" << binaryName
            << "_" << samplingRate << "_" << pid;
    if (!paramStr.empty()) {
        filename << "_" << paramStr;
    }

    outputFileNamePrefix = filename.str();

    filename << ".csv";

    return filename.str();
}

// Initialize output file
VOID InitOutputFile() {
    string filename = GetOutputFileName();
    outputFile.open(filename);
    if (!outputFile.is_open()) {
        cerr << "Error: Could not open file " << filename << endl;
        PIN_ExitApplication(1);
    }
    //outputFile << "=== Memory Usage Breakdown Per Function ===" << endl;
    outputFile << "FunctionName,MemUsageObs,UniqueAddresses,CountObs,SamplingInterval" << endl; 
}

// Adding fini function just to close the output file
VOID Fini(INT32 code, VOID* v)
{
    const UINT32 samplingRate = KnobSamplingInterval.Value();
    UINT64 totalProgramMem = 0; 
    UINT64 ObservationCount = 0;
    UINT32 numSplits = KnobNumSplits.Value(); 
    UINT32 splitSamplingRate = samplingRate * numSplits / KnobSampleReplication.Value();

    for(UINT32 j=0; j<numSplits; j++){
        // create output file for each split
        unordered_map<ADDRINT, UINT32> binMap;
        UINT64 binMem = 0;
        UINT64 binObservationCount = 0;
        ostringstream splitFileName;
        splitFileName << outputFileNamePrefix << "_SubSample_" << splitSamplingRate << "_bin_"<< j << ".csv";

        ofstream splitFile(splitFileName.str()); 

        splitFile << "FunctionName,MemUsageObs,UniqueAddresses,CountObs,SamplingInterval" << endl;
    
        for(UINT32 i=0; i<MAX_THREADS; i++){
            
            // output local count to the files, same format
            for(const auto &entry : MemoryUsage[i][j]){
                if(allThreadMap[entry.first] < entry.second){
                    totalProgramMem += (entry.second - allThreadMap[entry.first]);
                    allThreadMap[entry.first] = entry.second; 
                    //ObservationCount++;
                }
                if(binMap[entry.first] < entry.second){
                    binMem += (entry.second - binMap[entry.first]);
                    binMap[entry.first] = entry.second;
                }
            }
            binObservationCount += ObservationCount_perThread[i][j];
        }   

        // output the split file
        splitFile << "Total," << binMem << "," 
            << binMap.size() << ","
            << binObservationCount << "," 
            << splitSamplingRate << endl; 

    }
    
    for(int i = 0; i < MAX_THREADS; i++)
    {
        ObservationCount += GlobalObservationCount[i];
        
    }
    outputFile << "Total," << totalProgramMem << "," 
        << allThreadMap.size() << ","
        << ObservationCount << "," 
        << samplingRate << endl; 

    outputFile.close();
}
/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    cerr << "This tool demonstrates the basic use of the buffering API." << endl;
    cerr << endl << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */
/*!
 * The main procedure of the tool.
 * This function is called when the application image is loaded but not yet started.
 * @param[in]   argc            total number of elements in the argv array
 * @param[in]   argv            array of command line arguments,
 *                              including pin -t <toolname> -- ...
 */
int main(int argc, char* argv[])
{
    // Initialize PIN library. Print help message if -h(elp) is specified
    // in the command line or the command line is invalid
    if (PIN_Init(argc, argv))
    {
        return Usage();
    }

    // Initialize the memory reference buffer;
    // set up the callback to process the buffer.
    //
    bufId = PIN_DefineTraceBuffer(sizeof(struct MEMREF), NUM_BUF_PAGES, BufferFull, 0);

    if (bufId == BUFFER_ID_INVALID)
    {
        cerr << "Error: could not allocate initial buffer" << endl;
        return 1;
    }

    InitOutputFile();
    // add an instrumentation function
    TRACE_AddInstrumentFunction(Trace, 0);

    // add callbacks
    PIN_AddThreadStartFunction(ThreadStart, 0);
    PIN_AddThreadFiniFunction(ThreadFini, 0);

    PIN_AddFiniFunction(Fini, &outputFile);

    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}
