import json, os

base = r"C:\Users\Swetha S\OneDrive\Desktop\beginer project\log analyzer\log_generation\logs"
files = sorted(os.listdir(base))
for f in files:
    with open(os.path.join(base, f)) as fh:
        lines = fh.readlines()
        print(f"=== {f} ({len(lines)} entries) ===")
        for line in lines:
            entry = json.loads(line.strip())
            print(f"  {entry.get('timestamp','')}" + f" {entry.get('service',''):20s}" + f" {entry.get('level','')}" + f" {entry.get('message',''):30s}")
        print()