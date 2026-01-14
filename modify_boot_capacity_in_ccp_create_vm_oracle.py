from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove
import sys

capacity = sys.argv[1]
fh, abs_path = mkstemp()
with fdopen(fh,'w') as new_file:
    with open('ccp_create_vm_oracle.py') as old_file:
        lines = old_file.readlines()
        x = 0
        while x < len(lines):
            if lines[x] == 'bootcapacity = 300\n':
                new_file.write(f'bootcapacity = {capacity}\n')
                x +=1
            else:
                new_file.write(lines[x])
                x +=1
#Copy the file permissions from the old file to the new file
copymode('ccp_create_vm_oracle.py', abs_path)
#Remove original file
remove('ccp_create_vm_oracle.py')
#Move new file
move(abs_path, 'ccp_create_vm_oracle.py')
