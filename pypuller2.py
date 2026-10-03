import os

TARGET_FOLDER = "."
OUTPUT_PREFIX = "notepadofproject_part_"
MAX_SIZE_MB = 25
MAX_BYTES = MAX_SIZE_MB * 1024 * 1024

IGNORE_FOLDERS = {".git", "node_modules", "__pycache__", ".venv", "__EXPORT_SOURCES__zip"}

def dump_folder(folder):

    part = 1
    current_size = 0
    output_path = f"{OUTPUT_PREFIX}{part}.txt"
    out = open(output_path, "w", encoding="utf-8")

    for root, dirs, files in os.walk(folder):

        dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

        for file in files:

            path = os.path.join(root, file)

            block = []
            block.append("\n" + "="*80 + "\n")
            block.append(f"FILE: {path}\n")
            block.append("="*80 + "\n\n")

            try:
                with open(path, "r", encoding="utf-8") as f:
                    block.append(f.read())
            except:
                block.append("[binary or unreadable file]\n")

            block.append("\n\n")

            block_text = "".join(block)
            block_bytes = len(block_text.encode("utf-8"))

            if current_size + block_bytes > MAX_BYTES:
                out.close()
                part += 1
                output_path = f"{OUTPUT_PREFIX}{part}.txt"
                out = open(output_path, "w", encoding="utf-8")
                current_size = 0

            out.write(block_text)
            current_size += block_bytes

    out.close()

if __name__ == "__main__":
    dump_folder(TARGET_FOLDER)
    print("done -> split notepad files created (max 25mb each)")