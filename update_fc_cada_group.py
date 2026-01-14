#read input file
fin = open("create_vm.py", "rt")
#read file contents to string
data = fin.read()
#replace all occurrences of the required string
data = data.replace('BSD_CORE_HG_', 'BSD_CORE_HG_FC_')
#close the input file
fin.close()
#open the input file in write mode
fin = open("create_vm.py", "wt")
#overrite the input file with the resulting data
fin.write(data)
#close the file
fin.close()
