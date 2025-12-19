
import sys

def analyze_obj(filepath):
    print(f"Analyzing {filepath}...")
    usemtl_counts = {}
    group_counts = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('usemtl '):
                    mat = line.split()[1]
                    usemtl_counts[mat] = usemtl_counts.get(mat, 0) + 1
                elif line.startswith('g '):
                    grp = line.split()[1]
                    group_counts[grp] = group_counts.get(grp, 0) + 1
                    
        print("Materials used:")
        for k, v in usemtl_counts.items():
            print(f"  {k}: {v}")
            
        print("Groups:")
        for k, v in group_counts.items():
            print(f"  {k}: {v}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_obj(sys.argv[1])
    else:
        print("Usage: python script.py <obj_file>")
