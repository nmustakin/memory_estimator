/*
 * Copyright (C) 2012-2021 Intel Corporation.
 * SPDX-License-Identifier: MIT
 */

/*
 * This tool demonstrates the usage of the PIN_GetSourceLocation API from an instrumentation routine. You
 * may notice that there are no analysis routines in this example.
 *
 * Note: According to the Pin User Guide, calling PIN_GetSourceLocation from an analysis routine requires
 *       that the client lock be taken first.
 *
 */

#include <iostream>
#include <fstream>
#include "pin.H"
using std::string;

using std::cerr;
using std::cout;
using std::endl;
using std::ofstream;
using std::ostream;

/* ================================================================== */
// Global variables
/* ================================================================== */
PIN_LOCK printLock; 
UINT64 accessCounter = 0;
const ADDRINT startAddress = 0x1000;
const ADDRINT endAddress = 0x20000000;
UINT32 interval = 1;
/* ===================================================================== */
// Command line switches
/* ===================================================================== */

KNOB< string > KnobOutputFile(
    KNOB_MODE_WRITEONCE, "pintool", "o", "",
    "specify file name for the tool's output. If no filename is specified, the output will be directed to stdout.");

KNOB< UINT32 > KnobInterval(
    KNOB_MODE_WRITEONCE, "pintool", "i", "",
    "specify the interval of instrumentation. If no value is specified, value will default to 10");

/* ===================================================================== */
// Utilities
/* ===================================================================== */

// Print out help message.
INT32 Usage()
{
    cerr << "This tool demonstrates the usage of the PIN_GetSourceLocation API." << endl;
    cerr << endl << KNOB_BASE::StringKnobSummary() << endl;

    return -1;
}

// This is a utility function for acquiring and printing the source information.
static void RecordMemAccess (INS ins, ADDRINT address, ADDRINT memAddr, UINT32 memSize, ostream* printTo, bool* isLoad)
{
    if(INS_Valid(ins)){ // EDIT later to check within mem range
        accessCounter++;
        
	    if(accessCounter % interval == 0){ //Change to 100, 10000 as needed
            string filename; // This will hold the source file name.
            INT32 line = 0;  // This will hold the line number within the file.
    	    
	        PIN_LockClient();
	        PIN_GetSourceLocation(address, NULL, &line, &filename);
	        PIN_UnlockClient();
            
            PIN_GetLock(&printLock, 1);
	        //string fullOutput = StringFromAddrint(address) + " | MemAddr: " + StringFromAddrint(memAddr);
    	    *printTo << StringFromAddrint(address) << " | MemAddr: " << StringFromAddrint(memAddr);
            *printTo << " | MemSize: " << memSize;
	        if (!filename.empty())
    	    {
		        *printTo << " #" << filename << ":" << std::to_string(line);
    	    }
	        if(*isLoad) *printTo << " ! LOAD";
	        if(!(*isLoad)) *printTo << " ! STORE"; 
	        *printTo << endl; 
            PIN_ReleaseLock(&printLock);
	    }
    }
}

/* ===================================================================== */
// Instrumentation callbacks
/* ===================================================================== */

// Instrucmentation routine
static VOID InstrumentMemAccess(INS ins, VOID *v) {
    bool *isLoad = (bool*)malloc(sizeof(bool));
    if(INS_IsMemoryRead(ins)){
	*isLoad = true;
        for(unsigned int i = 0; i < INS_MemoryOperandCount(ins); i++){
	    if(INS_MemoryOperandIsRead(ins, i) || INS_MemoryOperandIsWritten(ins,i)){
	        INS_InsertCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemAccess,
	            IARG_INST_PTR,
		        IARG_INST_PTR,
     	        IARG_MEMORYOP_EA, i,
		        IARG_MEMORYREAD_SIZE, 
                IARG_PTR, static_cast<ostream*>(v),
		        IARG_PTR, isLoad,
                IARG_END
 	        );
	    }
	}
    }
    if(INS_IsMemoryWrite(ins)){
	*isLoad = false;
        for(unsigned int i = 0; i < INS_MemoryOperandCount(ins); i++){
	    if(INS_MemoryOperandIsRead(ins, i) || INS_MemoryOperandIsWritten(ins,i)){
	        INS_InsertCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemAccess,
	            IARG_INST_PTR,
		        IARG_INST_PTR,
     	        IARG_MEMORYOP_EA, i,
		        IARG_MEMORYWRITE_SIZE,
                IARG_PTR, static_cast<ostream*>(v),
		        IARG_PTR, isLoad,
                    IARG_END
 	        );
	    }
	}
    }
}

// IMG instrumentation routine - called once per image upon image load
static VOID ImageLoad(IMG img, VOID* v)
{
    // For simplicity, instrument only the main image. This can be extended to any other image of course.
    if (IMG_IsMainExecutable(img))
    {
        // To find all the instructions in the image, we traverse the sections of the image.
        for (SEC sec = IMG_SecHead(img); SEC_Valid(sec); sec = SEC_Next(sec))
        {
            // For each section, process all RTNs.
            for (RTN rtn = SEC_RtnHead(sec); RTN_Valid(rtn); rtn = RTN_Next(rtn))
            {
                // Many RTN APIs require that the RTN be opened first.
                RTN_Open(rtn);
                //output(RTN_Address(rtn), static_cast< ostream* >(v)); // Calls PIN_GetSourceLocation for the RTN address.

                // Call PIN_GetSourceLocation for all the instructions of the RTN.
                for (INS ins = RTN_InsHead(rtn); INS_Valid(ins); ins = INS_Next(ins))
                {
                    InstrumentMemAccess(ins, v);
		        }
                RTN_Close(rtn); // Don't forget to close the RTN once you're done.
            }
        }
    }
}

// Adding fini function just to close the output file
VOID Fini(INT32 code, VOID* v)
{
    if (!KnobOutputFile.Value().empty() && v != NULL)
    {
        static_cast< ofstream* >(v)->close();
    }
}

/* ===================================================================== */
// main
/* ===================================================================== */

int main(INT32 argc, CHAR** argv)
{
    PIN_InitSymbols();
    PIN_InitLock(&printLock);
    if (PIN_Init(argc, argv))
    {
        return Usage();
    }

    ofstream outFile;
    if (!KnobOutputFile.Value().empty())
    {
        outFile.open(KnobOutputFile.Value().c_str());
    }
    
    if (!KnobInterval.Value())
    {
        cout << "KnobInterval.Value()= " <<(UINT32)KnobInterval.Value();
        interval = (UINT32)KnobInterval.Value();
    }
    cout << "Sampling interval= " << interval <<endl; 

    IMG_AddInstrumentFunction(ImageLoad, (KnobOutputFile.Value().empty()) ? &cout : &outFile);

    // Register function to be called when the application exits
    PIN_AddFiniFunction(Fini, &outFile);

    // Never returns
    PIN_StartProgram();

    return 0;
}
