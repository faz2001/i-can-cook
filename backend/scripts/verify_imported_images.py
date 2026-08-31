"""
Companion to import_epicurious.py -- checks how many of the images that
import would actually need are present in your local
public/images/imported/ folder, before you run the import for real.

Regenerates the "needed" list directly from the CSV each run (same
title/ingredients/instructions/Image_Name filter as import_epicurious.py
itself), so it can't drift out of sync with a separately-saved manifest
file.

Usage (from backend_final_pkg, or anywhere -- paths are absolute/relative
to cwd as given):

    python3 scripts/verify_imported_images.py \\
        --csv path/to/Food_Ingredients_and_Recipe_Dataset_with_Image_Name_Mapping.csv \\
        --images-dir ../frontend_final_pkg/public/images/imported

Prints a coverage summary and writes still_missing.txt (one filename per
line) next to wherever you run it from, so you can re-run this after each
batch of copying and watch the missing count go down.
"""
import argparse
import csv
import os


def needed_image_filenames(csv_path: str) -> list[str]:
    needed = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Title") or "").strip()
            ingredients_raw = (row.get("Cleaned_Ingredients") or row.get("Ingredients") or "").strip()
            instructions_raw = (row.get("Instructions") or "").strip()
            if not title or not ingredients_raw or ingredients_raw == "[]" or not instructions_raw:
                continue
            img = (row.get("Image_Name") or "").strip()
            if img and not img.startswith("#"):
                needed.append(f"{img}.jpg")
    return needed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, help="Path to the Kaggle Epicurious CSV")
    parser.add_argument("--images-dir", required=True,
                         help="Path to check for <Image_Name>.jpg files, e.g. ../frontend_final_pkg/public/images/imported")
    parser.add_argument("--out", default="still_missing.txt", help="Where to write the list of still-missing filenames")
    args = parser.parse_args()

    needed = needed_image_filenames(args.csv)
    present = set(os.listdir(args.images_dir)) if os.path.isdir(args.images_dir) else set()

    missing = [n for n in needed if n not in present]

    print(f"Images directory: {args.images_dir}")
    print(f"  {'(does not exist yet -- create it before copying files in)' if not os.path.isdir(args.images_dir) else 'exists'}")
    print(f"Needed (per CSV, matching import_epicurious.py's own row filter): {len(needed)}")
    print(f"Present: {len(needed) - len(missing)}")
    print(f"Still missing: {len(missing)}")

    with open(args.out, "w", encoding="utf-8") as f:
        for name in missing:
            f.write(name + "\n")
    print(f"\nWrote {len(missing)} still-missing filenames to {args.out}")

    if missing:
        print("\nFirst 10 still missing:")
        for name in missing[:10]:
            print(" ", name)


if __name__ == "__main__":
    main()
