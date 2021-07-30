import subprocess
import re
import sys

print('Dry run:')


in_folder = sys.argv[1]
out_folder = sys.argv[2]

cmd = 'rsync -az --stats --dry-run ' + in_folder + ' ' + out_folder

proc = subprocess.Popen(cmd,
    shell=True,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)

output, err = proc.communicate()

mn = re.findall(r'Number of files: (\d+)', output.decode('utf-8'))
total_files = int(mn[0])

print('Number of files: ' + str(total_files))

print('Real rsync:')

cmd = 'rsync -avz  --progress ' + in_folder + ' ' + out_folder
proc = subprocess.Popen(cmd,
    shell=True,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)

while True:
    output = proc.stdout.readline().decode('utf-8')
    if 'to-check' in output:
        m = re.findall(r'to-check=(\d+)/(\d+)', output)
        progress = (100 * (int(m[0][1]) - int(m[0][0]))) / total_files
        sys.stdout.write('\rDone: ' + str(progress) + '%')
        sys.stdout.flush()
        if int(m[0][0]) == 0:
            break

print('\rFinished')
