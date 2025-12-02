import shutil
import os

source_fonts = r'node_modules\@fortawesome\fontawesome-free\webfonts'
dest_fonts = r'studio\static\studio\fontawesome\webfonts'

source_css = r'node_modules\@fortawesome\fontawesome-free\css\all.min.css'
dest_css = r'studio\static\studio\fontawesome\css\all.min.css'

try:
    if os.path.exists(source_fonts):
        if os.path.exists(dest_fonts):
            shutil.rmtree(dest_fonts)
        shutil.copytree(source_fonts, dest_fonts)
        print("Copied webfonts")
    else:
        print("Source fonts not found")

    if os.path.exists(source_css):
        os.makedirs(os.path.dirname(dest_css), exist_ok=True)
        shutil.copy2(source_css, dest_css)
        print("Copied css")
    else:
        print("Source css not found")

except Exception as e:
    print(f"Error: {e}")
