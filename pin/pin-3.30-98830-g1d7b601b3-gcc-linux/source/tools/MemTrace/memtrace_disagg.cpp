#include <stdio.h>
#include "pin.H"

PIN_LOCK printLock;
UINT64 accessCounter = 0;
ADDRINT startAddress = 0x1000; 
ADDRINT endAddress = 0x20000000;

static FILE* outfile = NULL;
static UINT32 interval = 10; 

void RecordMemAccess(VOID * ip, VOID *addr){
  //ADDRINT address = reinterpret_cast<ADDRINT>(addr);
  //if(address >= startAddress && address <= endAddress){
  if(true){
    accessCounter++; 
    if(accessCounter % interval == 0){ //Change to 100, 10000 as needed
      std::string fileName;
      INT32 lineNo = 0;
      PIN_LockClient();
      PIN_GetSourceLocation(reinterpret_cast<ADDRINT>(ip), nullptr, &lineNo, &fileName);
	      
      PIN_GetLock(&printLock, 1);
      fprintf(outfile, "Access at IP: %lx (LINE: %u) in file %s to %lx, count: %lu\n" , 
		       (UINT64)ip, lineNo, fileName.c_str(), (UINT64)addr, accessCounter); 
      //fprintf(outfile, "Access at IP: %lx to %lx, count %lu\n",
//		      (UINT64)ip, (UINT64)addr, accessCounter); 
      PIN_ReleaseLock(&printLock);
      PIN_UnlockClient();
      //printf("Access at %lx to %lx, count: %lu\n" , (UINT64)ip, (UINT64)addr, accessCounter); 
    }
  }
}

void Instruction(INS ins, VOID *v){
  if(INS_IsMemoryRead(ins) || INS_IsMemoryWrite(ins)){
    INS_InsertCall(
      ins, IPOINT_BEFORE, (AFUNPTR)RecordMemAccess,
      IARG_INST_PTR, 
      IARG_MEMORYOP_EA, 0,
      IARG_END
    );
  }
}


int main(int argc, char *argv[]){
  PIN_InitSymbols();
  PIN_Init(argc, argv);
  PIN_InitLock(&printLock);
  outfile = fopen("memtrace_disagg.log", "w+");
  INS_AddInstrumentFunction(Instruction, 0);
  PIN_StartProgram();
  return 0; 
}
